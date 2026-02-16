#!/usr/bin/env python3
"""
Supabase データベース自動セットアップ
"""
import os
from supabase import create_client, Client

# 接続情報
SUPABASE_URL = "https://bqibgtyymascetcgeeyw.supabase.co"
SUPABASE_KEY = "sb_secret_sDggrzEAIiKL6zNNu7VDIQ_0Pp-QHn1"

print("=" * 60)
print("Supabase データベースセットアップ")
print("=" * 60)

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase接続成功")
except Exception as e:
    print(f"❌ 接続失敗: {e}")
    exit(1)

# SQL実行用の関数
def execute_sql(sql, description):
    """SQLを実行"""
    try:
        print(f"\n{description}...")
        result = supabase.postgrest.rpc("exec_sql", {"sql": sql}).execute()
        print(f"✅ {description} 完了")
        return True
    except Exception as e:
        # rpc が使えない場合は直接実行を試みる
        try:
            # Supabaseの管理APIを使用
            import requests
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
                headers=headers,
                json={"sql": sql}
            )
            if response.status_code == 200:
                print(f"✅ {description} 完了")
                return True
            else:
                print(f"⚠️ {description}: {e}")
                return False
        except Exception as e2:
            print(f"⚠️ {description}: 手動で実行が必要です")
            print(f"   エラー: {e2}")
            return False

print("\n" + "=" * 60)
print("テーブル作成")
print("=" * 60)

# ユーザーテーブル作成
users_table_sql = """
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    api_key TEXT UNIQUE NOT NULL,
    subscription_status TEXT DEFAULT 'inactive',
    plan_type TEXT DEFAULT 'free',
    plan_limit INTEGER DEFAULT 0,
    monthly_usage INTEGER DEFAULT 0,
    total_usage INTEGER DEFAULT 0,
    stripe_customer_id TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP
);
"""

# 直接テーブル作成を試みる（Supabase Python クライアント経由）
try:
    print("\nユーザーテーブルを作成中...")
    # SQLファイルとして保存して実行する方法
    print("\n【重要】以下のSQLをSupabase SQL Editorで実行してください:")
    print("-" * 60)
    print(users_table_sql)
    print("-" * 60)
    
except Exception as e:
    print(f"⚠️ 自動作成できませんでした: {e}")

# テストデータ挿入
print("\n" + "=" * 60)
print("テストユーザー作成")
print("=" * 60)

try:
    # テストユーザーが既に存在するか確認
    existing = supabase.table("users").select("*").eq("email", "test@example.com").execute()
    
    if len(existing.data) == 0:
        # 新規作成
        import secrets
        test_api_key = f"ask_{secrets.token_hex(16)}"
        
        test_user = {
            "email": "test@example.com",
            "api_key": test_api_key,
            "subscription_status": "active",
            "plan_type": "pro",
            "plan_limit": 100,
            "monthly_usage": 0,
            "stripe_customer_id": "cus_test_123"
        }
        
        result = supabase.table("users").insert(test_user).execute()
        print(f"✅ テストユーザー作成成功")
        print(f"   Email: test@example.com")
        print(f"   API Key: {test_api_key}")
        print(f"   Plan: Pro (100記事/月)")
    else:
        print(f"✅ テストユーザーは既に存在します")
        print(f"   API Key: {existing.data[0]['api_key']}")
        
except Exception as e:
    print(f"⚠️ テストユーザー作成: {e}")
    print("\n以下のSQLをSupabase SQL Editorで実行してください:")
    print("-" * 60)
    print(f"""
INSERT INTO users (email, api_key, subscription_status, plan_type, plan_limit, stripe_customer_id)
VALUES ('test@example.com', 'ask_{secrets.token_hex(8)}', 'active', 'pro', 100, 'cus_test_123');
""")
    print("-" * 60)

print("\n" + "=" * 60)
print("セットアップ完了")
print("=" * 60)

# 接続テスト
print("\n接続テスト実行中...")
try:
    users = supabase.table("users").select("*").limit(5).execute()
    print(f"✅ 接続テスト成功！登録ユーザー数: {len(users.data)}")
    
    for user in users.data:
        print(f"  - {user['email']} ({user['plan_type']}, {user['monthly_usage']}/{user['plan_limit']})")
        
except Exception as e:
    print(f"⚠️ 接続テスト: テーブルがまだ作成されていません")
    print(f"   {e}")

print("\n" + "=" * 60)
print("次のステップ")
print("=" * 60)
print("1. Supabaseダッシュボード (https://bqibgtyymascetcgeeyw.supabase.co)")
print("2. 左メニューの「SQL Editor」をクリック")
print("3. 上記のSQLをコピー&ペーストして実行")
print("=" * 60)
