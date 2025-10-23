import json
import os
import boto3
import wave
from vosk import Model, KaldiRecognizer # type: ignore

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table_name = os.environ["TRANSCRIPTION_TABLE"]
table = dynamodb.Table(table_name)

MODEL_PATH = "/opt/python/vosk-model-small-en-us-0.15"
model = Model(MODEL_PATH)

def handler(event, context):
    for record in event['Records']:
        body = json.loads(record['body'])
        print("[DEBUG] Message body:", body)
        bucket = body['bucket']
        wav_key = body['wavKey']
        single_id = body['singleId']

        local_wav = f'/tmp/{os.path.basename(wav_key)}'
        
        print(f"[DEBUG] Downloading s3://{bucket}/{wav_key} -> {local_wav}")
        s3.download_file(bucket, wav_key, local_wav)
        print("[DEBUG] Download complete")

        print(model)
        print(local_wav)
        try:
            wf = wave.open(local_wav, "rb")
            print(f"[DEBUG] WAV opened: {wf.getnchannels()}ch, {wf.getframerate()}Hz")
            rec = KaldiRecognizer(model, wf.getframerate())

            transcription = ""
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    res = json.loads(rec.Result())
                    print(f"[DEBUG] Partial result: {res}")
                    transcription += res.get("text", "") + " "
                else:
                    partial = json.loads(rec.PartialResult())
                    print(f"[DEBUG] Partial: {partial}")
                    text = partial.get("partial", "")
                    if text:
                        print(f"[DEBUG] Partial -> {text}")
                        transcription += text + " "

            final_res = json.loads(rec.FinalResult())
            print(f"[DEBUG] Final result: {final_res}")
            final_text = final_res.get("text", "")
            if final_text:
                print(f"[DEBUG] Final -> {final_text}")
                transcription += final_text

            wf.close()
            print(f"[DEBUG] Final transcription: {transcription!r}")
            
            table.put_item(Item={
                "singleId": single_id,
                "transcription": transcription
            })
        finally:
            if os.path.exists(local_wav):
                os.unlink(local_wav)

        s3.delete_object(Bucket=bucket, Key=wav_key)
        print(f"[DEBUG] Deleted S3 temp file s3://{bucket}/{wav_key}")