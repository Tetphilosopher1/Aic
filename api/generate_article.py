#!/usr/bin/env python3
"""
AI記事生成API - Supabase認証版（修正版）
"""
import os
import sys
import json
from datetime import datetime
import anthropic
import requests

# 環境変数
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Supabase REST API用のヘッダー
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def verify_and_get_user(api_key):
    """APIキー検証とユーザー情報取得"""
    try:
        # Supabase REST APIで直接クエリ
        url = f"{SUPABASE_URL}/rest/v1/users?api_key=eq.{api_key}&select=*"
        response = requests.get(url, headers=SUPABASE_HEADERS)
        
        if response.status_code != 200:
            return {"error": f"API呼び出しエラー: {response.status_code}"}
        
        users = response.json()
        
        if not users or len(users) == 0:
            return {"error": "無効なAPIキーです"}
        
        user = users[0]
        
        # サブスクリプション確認
        if user["subscription_status"] != "active":
            return {"error": "有効なサブスクリプションが必要です"}
        
        # 使用量制限チェック
        if user["monthly_usage"] >= user["plan_limit"]:
            return {"error": f"月間使用制限に達しました ({user['monthly_usage']}/{user['plan_limit']})"}
        
        return user
        
    except Exception as e:
        return {"error": f"認証エラー: {str(e)}"}

def generate_article(topic, tone="professional", length=2000):
    """Claude APIで記事生成"""
    
    claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
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

以下のJSON形式のみで出力:
{{"title": "【初心者向け】タイトル", "content": "<h2>見出し</h2><p>本文</p>", "meta_description": "120文字の説明", "keywords": ["キーワード1", "キーワード2"]}}"""

    try:
        message = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text.strip()
        
        # JSONパース
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()
        
        article = json.loads(response_text)
        return article
        
    except Exception as e:
        return {"error": f"生成エラー: {str(e)}"}

def increment_usage(user_id, current_monthly, current_total):
    """使用量をカウントアップ"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}"
        data = {
            "monthly_usage": current_monthly + 1,
            "total_usage": current_total + 1,
            "last_used_at": datetime.now().isoformat()
        }
        response = requests.patch(url, headers=SUPABASE_HEADERS, json=data)
        return response.status_code == 200 or response.status_code == 204
    except:
        return False

def main():
    """メイン処理"""
    
    # 入力パラメータ取得
    api_key = os.getenv("INPUT_API_KEY")
    topic = os.getenv("INPUT_TOPIC")
    tone = os.getenv("INPUT_TONE", "professional")
    length = int(os.getenv("INPUT_LENGTH", "2000"))
    
    print("=" * 60)
    print("AI記事生成API")
    print("=" * 60)
    
    # 認証
    print("\n認証中...")
    user = verify_and_get_user(api_key)
    
    if "error" in user:
        result = {"success": False, "error": user["error"]}
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)
    
    print(f"✅ 認証成功: {user['email']} ({user['plan_type']})")
    print(f"使用量: {user['monthly_usage']}/{user['plan_limit']}")
    
    # 記事生成
    print(f"\n記事生成中: {topic}")
    article = generate_article(topic, tone, length)
    
    if "error" in article:
        result = {"success": False, "error": article["error"]}
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)
    
    # 使用量カウント
    increment_usage(user["id"], user["monthly_usage"], user["total_usage"])
    
    # 結果出力
    result = {
        "success": True,
        "data": article,
        "usage": {
            "used": user["monthly_usage"] + 1,
            "limit": user["plan_limit"],
            "remaining": user["plan_limit"] - user["monthly_usage"] - 1
        }
    }
    
    print("\n✅ 生成成功！")
    print(f"タイトル: {article['title']}")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
