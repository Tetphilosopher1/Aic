<?php
/**
 * Stripe Webhook Handler
 * 決済完了時の自動処理
 */

header('Content-Type: application/json');

// Stripeシークレットキー
define('STRIPE_SECRET_KEY', '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');
define('STRIPE_WEBHOOK_SECRET', 'whsec_YOUR_WEBHOOK_SECRET'); // 後で設定

// Supabase設定
define('SUPABASE_URL', 'https://bqibgtyymascetcgeeyw.supabase.co');
define('SUPABASE_KEY', 'sb_secret_sDggrzEAIiKL6zNNu7VDIQ_0Pp-QHn1');

// リクエストボディを取得
$payload = @file_get_contents('php://input');
$sig_header = $_SERVER['HTTP_STRIPE_SIGNATURE'] ?? '';

// Webhook署名を検証
try {
    require_once 'vendor/autoload.php';
    \Stripe\Stripe::setApiKey(STRIPE_SECRET_KEY);
    
    $event = \Stripe\Webhook::constructEvent(
        $payload, 
        $sig_header, 
        STRIPE_WEBHOOK_SECRET
    );
} catch(\UnexpectedValueException $e) {
    http_response_code(400);
    exit();
} catch(\Stripe\Exception\SignatureVerificationException $e) {
    http_response_code(400);
    exit();
}

// イベント処理
switch ($event->type) {
    case 'checkout.session.completed':
        handleCheckoutComplete($event->data->object);
        break;
        
    case 'customer.subscription.deleted':
        handleSubscriptionCanceled($event->data->object);
        break;
        
    case 'invoice.payment_succeeded':
        handlePaymentSucceeded($event->data->object);
        break;
}

http_response_code(200);

/**
 * 決済完了処理
 */
function handleCheckoutComplete($session) {
    $customer_email = $session->customer_email;
    $subscription_id = $session->subscription;
    $customer_id = $session->customer;
    
    // プラン情報を取得
    $subscription = \Stripe\Subscription::retrieve($subscription_id);
    $price_id = $subscription->items->data[0]->price->id;
    
    // プランマッピング
    $plans = [
        'price_1T1M2cFtS4gsy4qEKh1vCG26' => ['type' => 'starter', 'limit' => 30],
        'price_1T1M3dFtS4gsy4qEBmqLofCs' => ['type' => 'pro', 'limit' => 100],
        'price_1T1M4oFtS4gsy4qEN7nfk5TT' => ['type' => 'unlimited', 'limit' => 999999]
    ];
    
    $plan = $plans[$price_id] ?? ['type' => 'starter', 'limit' => 30];
    
    // APIキー生成
    $api_key = 'ask_' . bin2hex(random_bytes(16));
    
    // Supabaseにユーザー登録
    $user_data = [
        'email' => $customer_email,
        'api_key' => $api_key,
        'subscription_status' => 'active',
        'plan_type' => $plan['type'],
        'plan_limit' => $plan['limit'],
        'stripe_customer_id' => $customer_id,
        'stripe_subscription_id' => $subscription_id,
        'monthly_usage' => 0,
        'total_usage' => 0
    ];
    
    $ch = curl_init(SUPABASE_URL . '/rest/v1/users');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'apikey: ' . SUPABASE_KEY,
        'Authorization: Bearer ' . SUPABASE_KEY,
        'Content-Type: application/json',
        'Prefer: return=representation'
    ]);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($user_data));
    
    $response = curl_exec($ch);
    curl_close($ch);
    
    // ウェルカムメール送信
    sendWelcomeEmail($customer_email, $api_key, $plan['type']);
    
    // ログ記録
    error_log("New user registered: {$customer_email} with plan {$plan['type']}");
}

/**
 * サブスクリプション解約処理
 */
function handleSubscriptionCanceled($subscription) {
    $customer_id = $subscription->customer;
    
    // Supabaseでステータス更新
    $ch = curl_init(SUPABASE_URL . '/rest/v1/users?stripe_customer_id=eq.' . $customer_id);
    curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'PATCH');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'apikey: ' . SUPABASE_KEY,
        'Authorization: Bearer ' . SUPABASE_KEY,
        'Content-Type: application/json'
    ]);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode([
        'subscription_status' => 'canceled'
    ]));
    
    curl_exec($ch);
    curl_close($ch);
}

/**
 * 支払い成功処理（月次更新）
 */
function handlePaymentSucceeded($invoice) {
    $customer_id = $invoice->customer;
    
    // 使用量リセット
    $ch = curl_init(SUPABASE_URL . '/rest/v1/users?stripe_customer_id=eq.' . $customer_id);
    curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'PATCH');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'apikey: ' . SUPABASE_KEY,
        'Authorization: Bearer ' . SUPABASE_KEY,
        'Content-Type: application/json'
    ]);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode([
        'monthly_usage' => 0
    ]));
    
    curl_exec($ch);
    curl_close($ch);
}

/**
 * ウェルカムメール送信
 */
function sendWelcomeEmail($email, $api_key, $plan) {
    $subject = 'AI Content Studio へようこそ！';
    
    $message = "
AI Content Studio にご登録いただきありがとうございます！

【あなたのAPIキー】
{$api_key}

【プラン】
{$plan}

【使い方】
1. WordPress管理画面の「AI記事生成」メニューを開く
2. 「設定」でAPIキーを入力
3. トピックを入力して「記事を生成」

ご不明点がございましたら、お気軽にお問い合わせください。

--
AI Content Studio
https://tetphilosopher.com
    ";
    
    $headers = "From: AI Content Studio <noreply@tetphilosopher.com>\r\n";
    $headers .= "Content-Type: text/plain; ch
