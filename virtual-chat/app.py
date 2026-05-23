from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import google.generativeai as genai
import requests
import base64
import re
import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# 環境変数からAPIキーを取得（なければNone）
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# キーが読み込めているか確認
if not GEMINI_API_KEY:
    print("GEMINI_API_KEYが設定されていません")

SPEAKER_UUID = "コエイロインク"
STYLE_ID = 1283534946


# 1. Geminiの設定
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name='gemini-flash-latest',
    system_instruction=f"""
    一人称は｢俺｣
    タメ口で話す
    性格は優柔不断でのんびりした性格
    返答は2、3文で返す
    """
    )
chat = model.start_chat(history=[])

app = Flask(__name__)
CORS(app)

# 読み上げ
@app.route('/read', methods=['POST'])
def read_endpoint():
    try:
        data = request.json
        text = data.get("text", "")

        res_audio = requests.post(
            "http://localhost:50032/v1/predict",
            json={
                "speakerUuid": SPEAKER_UUID,
                "styleId": STYLE_ID,
                "text": text,
                "speedScale": 1.0,
                "pitchScale": 0.0,
                "intonationScale": 1.0,
                "volumeScale": 1.0,
                "prePhonemeLength": 0.1,
                "postPhonemeLength": 0.1,
                "outputSamplingRate": 44100
            }
        )

        audio_base64 = base64.b64encode(res_audio.content).decode('utf-8')
        return jsonify({"audio": audio_base64})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Geminiで返事
@app.route('/chat', methods=['POST'])
def chat_endpoint():
    try:
        data =request.json
        user_message = data.get("message", "")

        if not user_message:
            return jsonify({"error": "メッセージが空です"}), 400

        # ストリーミング生成
        def generate():
            response = chat.send_message(user_message, stream=True)

            buffer = ""
            for chunk in response:
                buffer += chunk.text

                while True:
                    match = re.match(r'(.*?[。！？\n]+)', buffer)

                    if match:
                        sentence = match.group(1)
                        buffer = buffer[len(sentence):]

                        clean_sentence = sentence.strip().replace('"', ' ').replace('\n', ' ').replace('\r', ' ')
                        if not clean_sentence:
                            continue

                        res_audio = requests.post(
                            "http://localhost:50032/v1/predict",
                            json={
                                "speakerUuid": SPEAKER_UUID,
                                "styleId": STYLE_ID,
                                "text": clean_sentence,
                                "speedScale": 1.0,
                                "pitchScale": 0.0,
                                "intonationScale": 1.0,
                                "volumeScale": 5.0,
                                "prePhonemeLength": 0.1,
                                "postPhonemeLength": 0.1,
                                "outputSamplingRate": 44100
                            }
                        )

                        if res_audio.status_code == 200:
                            audio_base64 = base64.b64encode(res_audio.content).decode('utf-8')
                            json_data = f'{{"answer": "{clean_sentence}", "audio": "{audio_base64}"}}'
                            yield json_data.strip() + "\n"
                    else:
                        break


            if buffer.strip():
                clean_sentence = buffer.strip().replace('"', ' ').replace('\n', ' ').replace('\r', ' ')
                if clean_sentence:
                    res_audio = requests.post(
                        "http://localhost:50032/v1/predict",
                        json={
                                "speakerUuid": SPEAKER_UUID,
                                "styleId": STYLE_ID,
                                "text": clean_sentence,
                                "speedScale": 1.0,
                                "pitchScale": 0.0,
                                "intonationScale": 1.0,
                                "volumeScale": 5.0,
                                "prePhonemeLength": 0.1,
                                "postPhonemeLength": 0.1,
                                "outputSamplingRate": 44100
                            }
                    )
                    
                    if res_audio.status_code == 200:
                        audio_base64 = base64.b64encode(res_audio.content).decode('utf-8')
                        json_data = f'{{"answer": "{clean_sentence}", "audio": "{audio_base64}"}}'
                        yield json_data.strip() + "\n"
                        
        return Response(stream_with_context(generate()), content_type='application/json')

    except Exception as e:
        print(f"エラー発生： {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)