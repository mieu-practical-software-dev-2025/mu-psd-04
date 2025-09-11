# --- ライブラリのインポート ---
import os
from flask import Flask, request, jsonify, send_from_directory
import json
from dotenv import load_dotenv
from openai import OpenAI

# --- 初期設定 ---
# .envファイルから環境変数を読み込む
load_dotenv()

# Flaskアプリケーションのインスタンスを作成
# static_folderのデフォルトは 'static' なので、
# このファイルと同じ階層に 'static' フォルダがあれば自動的にそこが使われます。
app = Flask(__name__)

# --- 開発用の設定 ---
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

# --- 環境変数の読み込み ---
# OpenRouter APIキーと関連情報を環境変数から取得
# このキーはサーバーサイドで安全に管理してください
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SITE_URL = os.getenv("YOUR_SITE_URL", "http://localhost:5000") # Default if not set
APP_NAME = os.getenv("YOUR_APP_NAME", "FlaskVueApp") # Default if not set

# --- ルーティング定義 ---

# URL:/ に対して、static/index.htmlを表示して
# クライアントサイドのVue.jsアプリケーションをホストする
@app.route('/')
def index():
    app.logger.info("Serving index.html")
    return send_from_directory(app.static_folder, 'index.html')

# アキネーターの質問・回答を生成するAPIエンドポイント
@app.route('/akinator_api', methods=['POST'])
def akinator_api():
    app.logger.info("akinator_api: a new request received.")

    # APIキーが設定されているかチェック
    if not OPENROUTER_API_KEY:
        app.logger.error("OpenRouter API key not configured.")
        return jsonify({"error": "OpenRouter API key is not configured on the server."}), 500
    # OpenRouter APIクライアントを初期化
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        default_headers={
            "HTTP-Referer": SITE_URL,
            "X-Title": APP_NAME,
        }
    )

    # フロントエンドから送信されたJSONデータを取得
    data = request.get_json()
    history = data.get('history', [])

    # これまでの対話履歴をテキスト形式に変換
    history_text = "\n".join([f"Q: {item['q']}\nA: {item['a']}" for item in history])
    
    # ユーザーが選択できる回答の選択肢
    user_choices = "「はい」「いいえ」「わからない」「たぶんそう」「部分的に違う」"

    # AIに与える指示（システムプロンプト）を定義
    system_prompt = f"""
あなたは、ユーザーが思い浮かべている人物やキャラクターを当てるゲーム「アキネーター」の魔人です。あなたには完璧な記憶力があり、過去の対話で得た情報を絶対に忘れません。
以下の思考プロセスとルールに厳密に従って、最適な応答をJSON形式で生成してください。

### 思考プロセス
1.  **現状分析**: 過去の全対話履歴をレビューし、確定した特徴（例：男性、コンビ芸人、九州出身）と否定された特徴（例：NSC出身ではない、コンビ名に漢字・英語・数字は含まない）を箇条書きで整理します。
2.  **仮説立案**: 分析結果に基づき、考えられる候補を複数（3〜5つ）リストアップします。
3.  **思考**:
    - 候補を最も効率的に区別できる質問は何か？（例：「コンビ名が2文字か3文字か」を個別に聞くのではなく、「コンビ名は食べ物に関係しますか？」と聞けば、より多くの候補を一度に絞り込めるかもしれない）
    - この質問は過去の質問と重複していないか？堂々巡りになっていないか？
    - 「いいえ」や「わからない」が連続している場合、現在の仮説（例：出身地で絞る）が有効でないと判断し、全く別の角度（例：芸風、見た目の特徴、趣味）からの質問に切り替える。
4.  **結論**: 上記の思考に基づき、生成する質問または最終回答を決定します。
5.  **最終回答の判断**: 候補が1つに絞り込めたと95%確信した場合、または質問回数が25回に達した場合にのみ、最終回答を生成します。

### ルール
1.  **質問**:
    - **質問形式**: 質問は必ず「はい」か「いいえ」で答えられる形式（クローズドクエスチョン）にしてください。「どのような」「なんの」といったオープンクエスチョンは固く禁じます。
    - **禁止事項**: 以下の質問は固く禁じます。
        - **最終確認の質問**: 特定の人物名を挙げて「〇〇ですか？」と質問すること。これは最終回答と見なします。
        - **重複・自明な質問**: 過去に尋ねた質問や、そこから導かれる自明な質問（例：「コンビ名に漢字は入っていますか？」→いいえ の後に「コンビ名はひらがなですか？」と聞くのではなく、「コンビ名は全てひらがなですか？」と聞くなど）。
        - **複合的な質問**: 複数の事柄を同時に問う質問（例：「俳優で、歌手でもありますか？」）。
    - 上記の思考プロセスとルールに従い、質の高い質問を1つだけ生成してください。
2.  **最終回答**:
    - 最終回答は、必ず具体的な人物名やキャラクター名（例：「大谷翔平」）にしてください。「野球選手」のような曖昧なカテゴリ名は禁止です。
    - 最終回答を生成する際は、必ず `{{"type": "answer", "text": "あなたの思い浮かべているのは「〇〇」ですね！"}}` の形式で出力してください。
3.  **出力形式**:
    - 応答は、必ず以下のJSON形式のいずれかとし、JSON以外のテキストは絶対に出力しないでください。
    - 質問の場合: `{{"type": "question", "text": "ここに質問文"}}`
    - 最終回答の場合: `{{"type": "answer", "text": "あなたの思い浮かべているのは「〇〇」ですね！"}}`

これまでの対話履歴:
{history_text}
"""

    # OpenRouter APIへのリクエストを実行
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "次の応答をJSON形式で生成してください。"}
            ],
            model="openai/gpt-4o-mini", # 応答性能が良いモデルを推奨
            response_format={"type": "json_object"}, # JSONモードを有効化
        )

        # AIからの応答をチェック
        if chat_completion.choices and chat_completion.choices[0].message and chat_completion.choices[0].message.content:
            response_text = chat_completion.choices[0].message.content
            app.logger.info(f"AI Response: {response_text}")
            app.logger.info("akinator_api: request processed successfully.")
            # AIの応答が正しいJSON形式かチェック
            try:
                response_json = json.loads(response_text)
                return jsonify(response_json)
            # JSONデコードエラーの処理
            except json.JSONDecodeError:
                app.logger.error(f"AI response is not a valid JSON: {response_text}")
                app.logger.info("akinator_api: request failed due to JSON decode error.")
                return jsonify({"error": "AIの応答が不正な形式でした。AIがルール通りに応答しなかった可能性があります。"}), 500
        # AIから空の応答が返ってきた場合の処理
        else:
            app.logger.error("AI response was empty.")
            app.logger.info("akinator_api: request failed due to empty AI response.")
            return jsonify({"error": "AIから有効な応答がありませんでした。"}), 500

    except Exception as e:
        app.logger.error(f"API call failed: {e}")
        return jsonify({"error": f"AIサービスとの通信中にエラーが発生しました。"}), 500
    
# 一つ前の質問に戻るためのAPIエンドポイント
@app.route('/undo_api', methods=['POST'])
def undo_api():
    app.logger.info("undo_api: a new request received.")

    # APIキーが設定されているかチェック
    if not OPENROUTER_API_KEY:
        app.logger.error("OpenRouter API key not configured.")
        return jsonify({"error": "OpenRouter API key is not configured on the server."}), 500

    # OpenRouter APIクライアントを初期化
    client = OpenAI( 
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        default_headers={
            "HTTP-Referer": SITE_URL,
            "X-Title": APP_NAME,
        }
    )

    # フロントエンドから送信されたJSONデータを取得
    data = request.get_json()
    history = data.get('history', [])

    # 履歴がない場合はエラーを返す
    if not history:
        return jsonify({"error": "履歴がないため、元に戻せません。"}), 400

    # 履歴の最後の項目（直前の回答）を削除
    history.pop()

    # 1つ前の状態の履歴をテキスト形式に変換
    history_text = "\n".join([f"Q: {item['q']}\nA: {item['a']}" for item in history])
    user_choices = "「はい」「いいえ」「わからない」「たぶんそう」「部分的に違う」"

    # AIに与える指示（システムプロンプト）を定義
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

    # OpenRouter APIへのリクエストを実行
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
        app.logger.info("undo_api: request processed successfully.")
        return jsonify(response_json)

    except Exception as e:
        app.logger.error(f"Undo API call failed: {e}")
        return jsonify({"error": "AIサービスとの通信中にエラーが発生しました。"}), 500

# --- アプリケーションの実行 ---
if __name__ == '__main__':
    if not OPENROUTER_API_KEY:
        print("警告: 環境変数 OPENROUTER_API_KEY が設定されていません。API呼び出しは失敗します。")
    app.run(debug=True, host='0.0.0.0', port=5000)