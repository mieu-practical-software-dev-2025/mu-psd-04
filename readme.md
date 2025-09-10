# アキネーター風アプリ

# 概要

このアプリケーションは、AIがユーザーの思い浮かべた人物やキャラクターを当てる「アキネーター風」のWebゲームです。

- フロントエンドに、Vue.js CDN版を用いています。

- バックエンドに、Python (Flask) を用い、OpenRouter経由で大規模言語モデル(LLM)のAPIを利用しています。

# 開発ツールインストール

- 管理者権限でコマンドプロンプトを起動します。

- 以下のコマンドを実行し、必要なソフトウェアを入手します。

```
winget install --id Git.Git -e --source winget
winget install --id Python.Python.3 -e --source winget
winget install --id Microsoft.VisualStudioCode -e --source winget
```

- vscodeを起動し、アクティビティバーの拡張機能から、以下のプラグインをインストールしてください。

  - Gemini Code Assist
  - Python
  - Vue.js Extension Pack

# 環境セットアップ

- [OpenRouter](https://openrouter.ai/)にアカウントを作成します。

- OpenRouterで、Keys → Create API Keys を選択、適当なキー名を付けて作成し、キー文字列をメモ帳等に保存しておきます。

- Python ライブラリインストール

  以下のコマンドでPythonの利用ライブラリをインストールします。

  ```sh
  pip install -r requirements.txt
  ```

# 実行方法

- example.envを.envにリネームして、OpenRouterのキーを記載してください。

- 以下のコマンドでサーバを起動します。

  ```sh
  python app.py
  ```

- ブラウザで以下のURLにアクセスしてみてください。

  ``` http://localhost:5000 ```

# アプリケーションの構成
- **`app.py`**: バックエンドのFlaskサーバーです。AIとの通信を仲介するAPIを提供します。
- **`static/index.html`**: フロントエンドのVue.jsアプリケーションです。ゲームのUIとロジックを管理します。
- **`.env`**: APIキーなどの機密情報を格納するファイルです。
- **`design-document.md`**: アプリケーションの仕様書です。

# 参考リンク

- [Flask](https://flask.palletsprojects.com/en/stable/)

  - Python で書かれた Webアプリケーションサーバ

- [Vue.js](https://vuejs.org/)

  - JavaScript製製のWebフロントエンド フレームワーク

- [Vue.js Tutorial](https://ja.vuejs.org/tutorial/)

  - Vue.jsの入門用チュートリアル
  
- [OpenAI API](https://github.com/openai/openai-python)

  - Pythonから、OpenAI APIを呼び出すライブラリ
