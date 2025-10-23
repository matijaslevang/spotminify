import json
import wave
import os
import boto3
from pydub import AudioSegment # type: ignore

s3 = boto3.client("s3")
sqs = boto3.client('sqs')
AudioSegment.converter = "/opt/python/ffmpeg"
AudioSegment.ffprobe = "/opt/python/ffprobe"

os.environ["PATH"] += os.pathsep + "/opt/python"
output_prefix = os.environ["OUTPUT_PREFIX"]
queue_url = os.environ["TRANSCRIBE_QUEUE_URL"]

def convert_to_wav(input_path: str, output_path: str):
    print(f"[DEBUG] Converting {input_path} -> {output_path}")
    audio = AudioSegment.from_file(input_path)
    print(f"[DEBUG] Original format: {audio.frame_rate} Hz, {audio.channels} channels, {len(audio)} ms")
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(output_path, format="wav")
    print("[DEBUG] Conversion complete")

def handler(event, context):
    for record in event['Records']:
        body = json.loads(record['body'])
        print("[DEBUG] SQS message body:", body)
        bucket = body['bucket']
        key = body['key']
        single_id = body['singleId']

        local_input = f"/tmp/{key.split('/')[-1]}"
        local_wav = f"/tmp/{os.path.splitext(key.split('/')[-1])[0]}.wav"

        print(f"[DEBUG] Downloading s3://{bucket}/{key} to {local_input}")
        s3.download_file(bucket, key, local_input)
        print("[DEBUG] Download complete")

        try:
            wf = wave.open(local_input, "rb")
            wf.close()
            print("[DEBUG] Input file is already WAV")
            local_wav = local_input  # already WAV
        except wave.Error:
            convert_to_wav(local_input, local_wav)
            print("[DEBUG] Input not WAV — converting")

        print(f"[DEBUG] Uploading {local_wav} to s3://{bucket}/{output_prefix}")
        output_key = f"{output_prefix}temp_{context.aws_request_id}.wav"
        s3.upload_file(local_wav, bucket, output_key)
        print(f"[DEBUG] full key: {output_key}")

        payload = {
            "wavKey": output_key,
            "singleId": single_id,
            "bucket": bucket
        }
        print("[DEBUG] Sending SQS message:", payload)
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(payload)
        )
        for f in [local_input, local_wav]:
            if os.path.exists(f) and f != local_input:
                os.unlink(f)
                print(f"[DEBUG] Deleted temp file {f}")