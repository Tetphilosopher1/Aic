#!/usr/bin/env python3
"""
AI記事生成API - Anthropic修正版
"""
import os
import sys
import json

# 簡易認証
VALID_API_KEYS = {
    "ask_test_demo_12345": {
        "email": "test@example.com",
        "plan": "pro",
        "limit": 100,
        "used": 0
    }
}

def verify_api_key(api_key):
    """APIキー検証"""
    if api_key in VALID_API_KEYS:
        return VALID_API_KEYS[api_key]
    return None

def generate_article(topic, tone="professional", length=2000):
    """Claude APIで記事生成"""
    
    # Anthropicクライアントを遅延インポート
    try:
        import anthropic
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"error": "ANTHROPIC_API_KEYが設定されていません"}
        
        client = anthropic.Anthropic(api_key=api_key)
        
    except ImportError as e:
        return {"error": f"anthropicライブラリのインポートエラー: {e}"}
    except Exception as e:
        return {"error": f"Anthropic初期化エラー: {e}"}
    
    prompt = f"""あなたはAI活用の専門家です。

テーマ: {topic}
トーン: {tone}
文字数: 約{length}文字

一般ユーザー向けに、実践的で役立つ記事を作成してください。

【要件】
- 専門用語は最小限に
- 具体的な使用例を豊富に
- 今日から試せる内容
- SEO最適化済み

以下のJSON形式のみで出力してください。マークダウンのコードブロックは不要です:
{{"title": "【初心者向け】タイトル32文字以内", "content": "<h2>見出し</h2><p>本文を{length}文字程度で</p>", "meta_description": "120文字の説明", "keywords": ["キーワード1", "キーワード2", "キーワード3"]}}"""

    try:
        print("Claude APIを呼び出し中...")
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )
        
        print("✅ Claude APIレスポンス受信")
        
        response_text = message.content[0].text.strip()
        print(f"レスポンス長: {len(response_text)}文字")
        
        # JSONパース
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()
        
        print("JSONパース中...")
        article = json.loads(response_text)
        print("✅ JSONパース成功")
        
        return article
        
    except json.JSONDecodeError as e:
        print(f"❌ JSONパースエラー: {e}")
        print(f"レスポンステキスト（最初の500文字）: {response_text[:500]}")
        return {"error": f"JSONパースエラー: {e}"}
    except Exception as e:
        print(f"❌ 生成エラー: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"生成エラー: {str(e)}"}

def main():
    """メイン処理"""
    
    # 入力パラメータ取得
    api_key = os.getenv("INPUT_API_KEY")
    topic = os.getenv("INPUT_TOPIC")
    tone = os.getenv("INPUT_TONE", "professional")
    length = int(os.getenv("INPUT_LENGTH", "2000"))
    
    print("=" * 60)
    print("AI記事生成API - デバッグ版")
    print("=" * 60)
    
    # 環境変数チェック
    print("\n環境変数チェック:")
    print(f"ANTHROPIC_API_KEY: {'設定済み' if os.getenv('ANTHROPIC_API_KEY') else '未設定'}")
    print(f"INPUT_API_KEY: {api_key}")
    print(f"INPUT_TOPIC: {topic}")
    
    # 認証
    print(f"\n認証中...")
    user = verify_api_key(api_key)
    
    if not user:
        result = {"success": False, "error": "無効なAPIキーです"}
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)
    
    print(f"✅ 認証成功: {user['email']} ({user['plan']})")
    print(f"使用量: {user['used']}/{user['limit']}")
    
    # 記事生成
    print(f"\n記事生成開始...")
    print(f"トピック: {topic}")
    print(f"トーン: {tone}")
    print(f"文字数: {length}")
    
    article = generate_article(topic, tone, length)
    
    if "error" in article:
        result = {"success": False, "error": article["error"]}
        print("\n" + "=" * 60)
        print("❌ 失敗")
        print("=" * 60)
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)
    
    # 結果出力
    result = {
        "success": True,
        "data": article,
        "usage": {
            "used": user['used'] + 1,
            "limit": user['limit'],
            "remaining": user['limit'] - user['used'] - 1
        }
    }
    
    print("\n" + "=" * 60)
    print("✅ 生成成功！")
    print("=" * 60)
    print(f"タイトル: {article['title']}")
    print(f"キーワード: {', '.join(article.get('keywords', []))}")
    print(f"本文長: {len(article.get('content', ''))}文字")
    print(f"\n--- 完全な結果 (JSON) ---")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
