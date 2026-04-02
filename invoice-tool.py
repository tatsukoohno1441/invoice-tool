import streamlit as st
import pandas as pd
import io

# ページ設定 (Page Config)
st.set_page_config(page_title="注文配送データ処理システム", page_icon="📦")

# --- 【ツール：ファイル読み込み関数】 ---
def secure_read(file):
    """自動的にエンコーディングを判別してCSVを読み込む（全ての列を文字列として保持）"""
    encodings = ['utf-8-sig', 'shift-jis', 'cp932', 'utf-8']
    for enc in encodings:
        try:
            file.seek(0)
            # dtype=str により、前方の0（00...）が消えるのを防ぎます
            df = pd.read_csv(file, encoding=enc, sep=None, engine='python', dtype=str)
            if df.shape[1] > 1:
                return df, f"{enc} で読み込み成功"
        except Exception:
            continue
    file.seek(0)
    return pd.read_csv(file, encoding='utf-8-sig', dtype=str), "utf-8-sig で読み込み（デフォルト）"

# --- 【メイン画面】 ---
st.title("注文＆配送データ自動処理ツール 🧡")
st.write("OrderファイルとDeliveryファイルをアップロードしてください。JANコードの補完、数量の連結、並べ替え、前方の0保持などの処理を自動で行います。")

# 1. ファイルアップロード
col1, col2 = st.columns(2)
with col1:
    order_file = st.file_uploader("Orderファイルをアップロード (CSV)", type=['csv'])
with col2:
    delivery_file = st.file_uploader("Deliveryファイルをアップロード (CSV)", type=['csv'])

if order_file and delivery_file:
    process_logs = []
    error_occurred = False

    try:
        # データ読み込み
        df_order, order_msg = secure_read(order_file)
        process_logs.append(f"✅ Orderファイル: {order_msg}")
        
        df_delivery, delivery_msg = secure_read(delivery_file)
        process_logs.append(f"✅ Deliveryファイル: {delivery_msg}")

        # --- 処理ロジック開始 ---

        # 1. OrderファイルのJANコード補完
        if 'JANコード' in df_order.columns and '商品コード' in df_order.columns:
            df_order['JANコード'] = df_order['JANコード'].replace(['nan', 'None', '<NA>', ''], pd.NA)
            df_order['JANコード'] = df_order['JANコード'].fillna(df_order['商品コード'])
            process_logs.append("✅ OrderファイルのJANコード補完が完了しました（0埋め保持）")

        # 2. JANコード * 数量 を Deliveryファイルの「品名２」へ
        if all(col in df_order.columns for col in ['注文番号', 'JANコード', '数量']) and '品名２' in df_delivery.columns:
            
            # 注文番号で昇順ソート
            df_order_sorted = df_order.sort_values(by='注文番号').reset_index(drop=True)
            
            # 数量の整形（1.0 などを 1 に変換）
            def format_qty(x):
                try:
                    return str(int(float(x)))
                except:
                    return str(x)
            
            # JAN*数量 の結合
            combined_list = (
                df_order_sorted['JANコード'] + "*" + df_order_sorted['数量'].apply(format_qty)
            ).tolist()
            
            # Deliveryファイルへ書き込み
            df_delivery['品名２'] = df_delivery['品名２'].astype(object)
            rows_to_fill = min(len(df_delivery), len(combined_list))
            df_delivery.iloc[:rows_to_fill, df_delivery.columns.get_loc('品名２')] = combined_list[:rows_to_fill]
            process_logs.append(f"✅ JANコード*数量の連結が完了しました (例: {combined_list[0] if combined_list else 'N/A'})")
        
        # 3. 品名２で降順ソート
        if '品名２' in df_delivery.columns:
            df_delivery = df_delivery.sort_values(by='品名２', ascending=False)
            process_logs.append("✅ 品名２で降順に並べ替えました")

        # 4. お届け先電話番号の補完
        if 'お届け先電話番号' in df_delivery.columns:
            df_delivery['お届け先電話番号'] = df_delivery['お届け先電話番号'].replace(['nan', 'None', ''], pd.NA)
            df_delivery['お届け先電話番号'] = df_delivery['お届け先電話番号'].fillna('048-299-7267')
            process_logs.append("✅ 空白の「お届け先電話番号」を補完しました")

        # --- 処理ロジック終了 ---

    except Exception as e:
        error_occurred = True
        process_logs.append(f"❌ 処理中にエラーが発生しました: {str(e)}")

    # --- 処理結果の表示 ---
    st.divider()
    st.subheader("🛠 処理ログ")
    for log in process_logs:
        if "❌" in log: st.error(log)
        elif "⚠️" in log: st.warning(log)
        else: st.info(log)

    if not error_occurred:
        st.success("🎉 処理が正常に完了しました！前方の0（00...）も保持されています。")
        output = io.BytesIO()
        df_delivery.to_csv(output, index=False, encoding='utf-8-sig')
        processed_data = output.getvalue()

        st.download_button(
            label="✨ 処理済みDeliveryファイルをダウンロード",
            data=processed_data,
            file_name="processed_delivery_final.csv",
            mime="text/csv"
        )
    else:
        st.error("エラーのため、ファイルを作成できませんでした。")

else:
    st.info("ファイルをアップロードしてください... 🧡")