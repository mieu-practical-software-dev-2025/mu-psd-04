import os
from flask import Flask, request, jsonify, send_from_directory
import json
from openai import OpenAI # Import the OpenAI library
from dotenv import load_dotenv
from openai import OpenAI

# .envファイルから環境変数を読み込む
load_dotenv()

# Flaskアプリケーションのインスタンスを作成
# static_folderのデフォルトは 'static' なので、
# このファイルと同じ階層に 'static' フォルダがあれば自動的にそこが使われます。
app = Flask(__name__)


# 開発モード時に静的ファイルのキャッシュを無効にする
if app.debug:
    @app.after_request
    def add_cache_control(response):
        # /static/ 以下のファイルに対するリクエストの場合
        if request.endpoint == 'static':
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache' # HTTP/1.0 backward compatibility
            response.headers['Expires'] = '0' # Proxies

        return response


# OpenRouter APIキーと関連情報を環境変数から取得
# このキーはサーバーサイドで安全に管理してください
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SITE_URL = os.getenv("YOUR_SITE_URL", "http://localhost:5000") # Default if not set
APP_NAME = os.getenv("YOUR_APP_NAME", "FlaskVueApp") # Default if not set

# URL:/ に対して、static/index.htmlを表示して
    # クライアントサイドのVue.jsアプリケーションをホストする
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/akinator_api', methods=['POST'])
def akinator_api():
    if not OPENROUTER_API_KEY:
        app.logger.error("OpenRouter API key not configured.")
        return jsonify({"error": "OpenRouter API key is not configured on the server."}), 500

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        default_headers={
            "HTTP-Referer": SITE_URL,
            "X-Title": APP_NAME,
        }
    )

    data = request.get_json()
    history = data.get('history', [])

    # プロンプトを作成
    history_text = "\n".join([f"Q: {item['q']}\nA: {item['a']}" for item in history])
    
    # ユーザーの回答選択肢を3つに絞る
    user_choices = "「はい」「いいえ」「わからない」「たぶんそう」「部分的に違う」"

    system_prompt = f"""
あなたは有名な「アキネーター」のように、ユーザーが思い浮かべている人物やキャラクターを当てる専門家です。
以下のルールに厳密に従って、JSON形式で応答してください。
### ルール
1.  **質問**: 履歴を分析し、対象を絞り込むための最も効果的な質問を生成します。履歴が空なら一般的な質問から始めます。（例: 「そのキャラクターは人間ですか？」）
    - **質問文には「〇〇」のような伏せ字やプレースホルダーを含めず、常に完全な文章で質問してください。**
    - **質問は、必ずユーザーが「はい」「いいえ」「わからない」「たぶんそう」「部分的に違う」の5択で答えられる形式にしてください。**「名前を教えてください」のような、答えを直接尋ねる質問は絶対に禁止です。
    - **単なる名前当ての質問（例：「そのキャラクターは〇〇ですか？」）を繰り返すことは禁止です。**代わりに、対象の属性や特徴（例：「そのキャラクターは〇〇に所属していますか？」）を尋ねる質問をしてください。
2.  **最終回答**: 以下のいずれかの条件を満たした場合、質問ではなく最終的な答えを提示してください。
    - 対象が99%以上の確率で特定できたと確信したとき。
    - **質問回数が30回に達したとき。** その時点で最も可能性が高いと思われる答えを提示してください。
    - **最終回答は、必ず具体的な人物名やキャラクター名（例：「大谷翔平」「ドラえもん」）にしてください。**「野球選手」のような、あいまいなカテゴリ名での回答は禁止します。
3.  **出力形式**: 応答は必ず以下のいずれかのJSON形式で出力してください。JSON以外のテキストは絶対に出力しないでください。
    - 質問の場合: `{{"type": "question", "text": "ここに質問文"}}`
    - 回答の場合: `{{"type": "answer", "text": "あなたの思い浮かべているのは「〇〇」ですね！"}}`

これまでの対話履歴:
{history_text}
"""

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "次の応答をJSON形式で生成してください。"}
            ],
            model="openai/gpt-4o-mini", # 応答性能が良いモデルを推奨
            response_format={"type": "json_object"}, # JSONモードを有効化
        )

        if chat_completion.choices and chat_completion.choices[0].message and chat_completion.choices[0].message.content:
            response_text = chat_completion.choices[0].message.content
            app.logger.info(f"AI Response: {response_text}")
            try:
                response_json = json.loads(response_text)
                return jsonify(response_json)
            except json.JSONDecodeError:
                app.logger.error(f"AI response is not a valid JSON: {response_text}")
                return jsonify({"error": "AIの応答が不正な形式でした。AIがルール通りに応答しなかった可能性があります。"}), 500
        else:
            app.logger.error("AI response was empty.")
            return jsonify({"error": "AIから有効な応答がありませんでした。"}), 500

    except Exception as e:
        app.logger.error(f"API call failed: {e}")
        return jsonify({"error": f"AIサービスとの通信中にエラーが発生しました。"}), 500
    
@app.route('/undo_api', methods=['POST'])
def undo_api():
    if not OPENROUTER_API_KEY:
        app.logger.error("OpenRouter API key not configured.")
        return jsonify({"error": "OpenRouter API key is not configured on the server."}), 500

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        default_headers={
            "HTTP-Referer": SITE_URL,
            "X-Title": APP_NAME,
        }
    )

    data = request.get_json()
    history = data.get('history', [])

    if not history:
        return jsonify({"error": "履歴がないため、元に戻せません。"}), 400

    # 履歴の最後の項目を削除
    history.pop()

    # 1つ前の状態の履歴から、再度質問を生成させる
    history_text = "\n".join([f"Q: {item['q']}\nA: {item['a']}" for item in history])
    user_choices = "「はい」「いいえ」「わからない」「たぶんそう」「部分的に違う」"

    system_prompt = f"""
あなたは「アキネーター」です。ユーザーが一つ前の状態に戻りたがっています。
以下の対話履歴を元に、**もう一度同じ質問を生成してください**。
絶対に新しい質問を考えてはいけません。

### ルール
1.  応答は `{{"type": "question", "text": "ここに質問文"}}` のJSON形式で出力してください。
2.  JSON以外のテキストは絶対に出力しないでください。

これまでの対話履歴:
{history_text}
"""

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "この履歴の次に続くべき質問を、もう一度生成してください。"}
            ],
            model="openai/gpt-4o-mini",
            response_format={"type": "json_object"},
        )
        response_text = chat_completion.choices[0].message.content
        response_json = json.loads(response_text)
        return jsonify(response_json)

    except Exception as e:
        app.logger.error(f"Undo API call failed: {e}")
        return jsonify({"error": "AIサービスとの通信中にエラーが発生しました。"}), 500

# URL:/send_api に対するメソッドを定義
@app.route('/send_api', methods=['POST'])
def send_api():
    if not OPENROUTER_API_KEY:
        app.logger.error("OpenRouter API key not configured.")
        return jsonify({"error": "OpenRouter API key is not configured on the server."}), 500

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        default_headers={ # Recommended by OpenRouter
            "HTTP-Referer": SITE_URL,
            "X-Title": APP_NAME,
        }
    )
    

    # POSTリクエストからJSONデータを取得
    data = request.get_json()

    # 'text'フィールドがリクエストのJSONボディに存在するか確認
    if not data or 'text' not in data:
        app.logger.error("Request JSON is missing or does not contain 'text' field.")
        return jsonify({"error": "Missing 'text' in request body"}), 400

    received_text = data['text']
    if not received_text.strip(): # 空文字列や空白のみの文字列でないか確認
        app.logger.error("Received text is empty or whitespace.")
        return jsonify({"error": "Input text cannot be empty"}), 400
    

    # contextがあればsystemプロンプトに設定、なければデフォルト値
    system_prompt = "140字以内で回答してください。" # デフォルトのシステムプロンプト
    if 'context' in data and data['context'] and data['context'].strip():
        system_prompt = data['context'].strip()
        app.logger.info(f"Using custom system prompt from context: {system_prompt}")
    else:
        app.logger.info(f"Using default system prompt: {system_prompt}")

    try:
        # OpenRouter APIを呼び出し
        # モデル名はOpenRouterで利用可能なモデルを指定してください。
        # 例: "mistralai/mistral-7b-instruct", "google/gemini-pro", "openai/gpt-3.5-turbo"
        # 詳細はOpenRouterのドキュメントを参照してください。
        chat_completion = client.chat.completions.create(
            messages=[ # type: ignore
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": received_text}
            ], # type: ignore
            model="openai/gpt-3.5-turbo", 
        ) # type: ignore
        


        # APIからのレスポンスを取得
        if chat_completion.choices and chat_completion.choices[0].message:
            processed_text = chat_completion.choices[0].message.content
        else:
            processed_text = "AIから有効な応答がありませんでした。"
            

        return jsonify({"message": "AIによってデータが処理されました。", "processed_text": processed_text})

    except Exception as e:
        app.logger.error(f"OpenRouter API call failed: {e}")
        # クライアントには具体的なエラー詳細を返しすぎないように注意
        return jsonify({"error": f"AIサービスとの通信中にエラーが発生しました。"}), 500

# スクリプトが直接実行された場合にのみ開発サーバーを起動
if __name__ == '__main__':
    if not OPENROUTER_API_KEY:
        print("警告: 環境変数 OPENROUTER_API_KEY が設定されていません。API呼び出しは失敗します。")
    app.run(debug=True, host='0.0.0.0', port=5000)


@app.route('/get_question', methods=['GET'])
def get_question():
    # ここに質問を返すロジックを実装します
    # 例えば、質問のリストからランダムに選択するか、
    # 以前の回答に基づいて次の質問を選択します
    question = "好きな色は何ですか？"  # これはサンプルです
    return jsonify({"question": question})


@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    data = request.get_json()
    if not data or 'answer' not in data or 'question' not in data:
        return jsonify({"error": "Missing 'answer' or 'question' in request body"}), 400

    answer = data['answer']
    question = data['question']

    # AIに質問を送信して次の質問を取得するか、
    # 推測を行うロジックをここに実装します
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
            default_headers={  # Recommended by OpenRouter
                "HTTP-Referer": SITE_URL,
                "X-Title": APP_NAME,
            }
        )

        chat_completion = client.chat.completions.create(
            model="google/gemma-3-27b-it:free",
            messages=[
                {"role": "system", "content": "あなたはアキネーターです。質問に答えてください。"},
                {"role": "user", "content": f"質問: {question}, 回答: {answer}"}
            ]
        )  # type: ignore

        ai_response = chat_completion.choices[0].message.content if chat_completion.choices else "回答が得られませんでした。"

        return jsonify({"response": ai_response})

    except Exception as e:
        app.logger.error(f"OpenRouter API call failed: {e}")
        return jsonify({"error": "AIサービスとの通信中にエラーが発生しました。"}), 500