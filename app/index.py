import base64
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

TABLE = os.environ['TABLE_NAME']
DDB = boto3.client('dynamodb')
IS_COLD = True
ENVIRONMENT_ID = str(uuid.uuid4())
HTML = '__HTML__'


def lambda_handler(event, context):
    global IS_COLD
    cold, IS_COLD = IS_COLD, False
    started = time.perf_counter()
    rid = context.aws_request_id
    http = event.get('requestContext', {}).get('http', {})
    method, path = http.get('method'), event.get('rawPath', http.get('path', '/'))

    def response(status, payload):
        payload.update(cold_start=cold, request_id=rid, environment_id=ENVIRONMENT_ID,
                       handler_ms=round((time.perf_counter() - started) * 1000, 3))
        # No patient information or event body is logged.
        print(json.dumps({'event': 'request', 'request_id': rid, 'status': status,
                          'cold_start': cold, 'environment_id': ENVIRONMENT_ID,
                          'handler_ms': payload['handler_ms']}))
        return {'statusCode': status, 'headers': {
            'content-type': 'application/json', 'cache-control': 'no-store',
            'x-content-type-options': 'nosniff'}, 'body': json.dumps(payload)}

    if method == 'GET' and path == '/':
        return {'statusCode': 200, 'headers': {
            'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store',
            'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY',
            'content-security-policy': "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"
        }, 'body': HTML}
    if method == 'GET' and path == '/health':
        return response(200, {'status': 'ok', 'region': os.environ.get('AWS_REGION'),
                              'note': 'Function health only; booking tests verify the database.'})
    if method != 'POST' or path != '/book':
        return response(404, {'error': 'Route not found'})
    try:
        raw = event.get('body') or ''
        if len(raw) > 6000:
            return response(413, {'error': 'Request too large'})
        if event.get('isBase64Encoded'):
            raw = base64.b64decode(raw, validate=True).decode('utf-8')
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError('JSON object required')
        patient, doctor, slot = (body.get(k) for k in ('patient', 'doctor', 'slot'))
        if not all(isinstance(v, str) and v.strip() for v in (patient, doctor, slot)):
            raise ValueError('patient, doctor and slot must be nonempty strings')
        patient, doctor, slot = patient.strip(), doctor.strip(), slot.strip()
        if len(patient) > 80 or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', doctor):
            raise ValueError('Patient: max 80 characters; doctor: letters, digits, hyphen, underscore, max 80')
        if len(slot) > 40:
            raise ValueError('Invalid slot')
        dt = datetime.fromisoformat(slot.replace('Z', '+00:00'))
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError('Slot must include a timezone offset')
        dt = dt.astimezone(timezone.utc)
        if dt.second or dt.microsecond or dt.minute not in (0, 30):
            raise ValueError('Choose an exact half-hour slot')
        if dt <= datetime.now(timezone.utc):
            raise ValueError('Slot must be in the future')
        canonical = dt.isoformat(timespec='seconds').replace('+00:00', 'Z')
    except (ValueError, TypeError, UnicodeError) as exc:
        return response(400, {'error': str(exc)})

    key = doctor + '#' + canonical
    try:
        DDB.put_item(TableName=TABLE, Item={
            'slot_key': {'S': key}, 'doctor': {'S': doctor},
            'slot': {'S': canonical}, 'patient': {'S': patient},
            'booked_at': {'S': datetime.now(timezone.utc).isoformat()},
        }, ConditionExpression='attribute_not_exists(slot_key)')
        return response(201, {'status': 'booked', 'slot_key': key})
    except ClientError as exc:
        if exc.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return response(409, {'status': 'already_booked', 'slot_key': key})
        print(json.dumps({'event': 'database_error', 'request_id': rid,
                          'code': exc.response['Error']['Code']}))
        return response(503, {'error': 'Database unavailable; retry later'})
