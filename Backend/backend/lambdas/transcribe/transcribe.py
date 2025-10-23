import json
import os
import boto3
import wave
from vosk import Model, KaldiRecognizer # type: ignore

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table_name = os.environ["TRANSCRIPTION_TABLE"]
table = dynamodb.Table(table_name)

MODEL_PATH = "/opt/vosk-model-small-en-us-0.15"
model = Model(MODEL_PATH)

def handler(event, context):
    for record in event['Records']:
        body = json.loads(record['body'])
        print(body)
        bucket = body['bucket']
        key = body['key']
        single_id = body['singleId']

        local_path = f"/tmp/{key.split('/')[-1]}"
        s3.download_file(bucket, key, local_path)

        wf = wave.open(local_path, "rb")
        rec = KaldiRecognizer(model, wf.getframerate())

        transcription = ""
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                transcription += res.get("text", "") + " "
        final_res = json.loads(rec.FinalResult())
        transcription += final_res.get("text", "")

        print(transcription)
        
        table.put_item(Item={
            "singleId": single_id,
            "transcription": transcription
        })