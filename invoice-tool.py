import streamlit as st
import pandas as pd
import io

# ページ設定
st.set_page_config(page_title="注文配送データ処理システム", page_icon="📥")

# --- 【ツール：ファイル読み込み関数】 ---
def secure_read(file):
    encodings = ['utf-8-sig', 'shift-jis', 'cp932', 'utf-8']
    for enc in encodings:
        try:
            file.seek(0)
            # 全て文字列として読み込み、前方の0を保持
            df = pd.read_csv(file, encoding=enc, sep=None, engine='python', dtype=str)
            if df.shape[1] > 1:
                return df, f"{enc} で読み込み成功"
        except Exception:
            continue
    file.seek(0)
    return pd.read_csv(file, encoding='utf-8-sig', dtype=str), "utf-8-sig で読み込み（デフォルト）"

# --- 【メイン画面】 ---
st.title("注文配送データ自動処理ツール 🧡")
st.write("OrderファイルとDeliveryファイルをアップロードしてください。注文番号をキーにしてデータを正確に紐付けます。")

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
        # 1. データ読み込み
        df_order, order_msg = secure_read(order_file)
        process_logs.append(f"✅ Orderファイル: {order_msg}")
        
        df_delivery, delivery_msg = secure_read(delivery_file)
        process_logs.append(f"✅ Deliveryファイル: {delivery_msg}")

        # --- 処理ロジック開始 ---

        # 2. OrderファイルのJANコード補完 (需求 1)
        if 'JANコード' in df_order.columns and '商品コード' in df_order.columns:
            df_order['JANコード'] = df_order['JANコード'].replace(['nan', 'None', '<NA>', ''], pd.NA)
            # 空白があれば商品コードをコピー
            df_order['JANコード'] = df_order['JANコード'].fillna(df_order['商品コード'])
            process_logs.append("✅ Order内のJANコードを商品コードで補完しました")
        else:
            st.error("Orderファイルに「JANコード」または「商品コード」列が見つかりません。")
            st.stop()

        # 3. 数量付きJANコードの作成
        if '数量' in df_order.columns:
            def format_qty(x):
                try: return str(int(float(x)))
                except: return str(x)
            
            # 「JAN*数量」の形式を作成
            df_order['processed_jan'] = df_order['JANコード'].astype(str) + "*" + df_order['数量'].apply(format_qty)
        else:
            st.error("Orderファイルに「数量」列が見つかりません。")
            st.stop()

        # 4. 【注文番号】をキーにDeliveryへ紐付け (需求 2)
        if '注文番号' in df_order.columns and '注文番号' in df_delivery.columns:
            # Order側で同じ注文番号が複数ある場合を考慮し、1つのセルにまとめます（例：JAN*1, JAN*2）
            df_order_grouped = df_order.groupby('注文番号')['processed_jan'].apply(lambda x: ', '.join(x)).reset_index()
            
            # DeliveryファイルにOrderのデータを結合 (Left Join)
            df_delivery = df_delivery.merge(df_order_grouped, on='注文番号', how='left')
            
            # 結合したデータを「品名２」に代入し、一時的な列を削除
            if '品名２' in df_delivery.columns:
                df_delivery['品名２'] = df_delivery['processed_jan']
                df_delivery = df_delivery.drop(columns=['processed_jan'])
                process_logs.append("✅ 注文番号をキーにしてJANコードを正確に紐付けました")
            else:
                st.error("Deliveryファイルに「品名２」列が見つかりません。")
                st.stop()
        else:
            st.error("両方のファイルに共通の「注文番号」列が必要です。")
            st.stop()

        # 5. 品名２で降順ソート (需求 3)
        # ソートしても行全体の整合性は保持されます
        df_delivery = df_delivery.sort_values(by='品名２', ascending=False).reset_index(drop=True)
        process_logs.append("✅ 品名２の降順で全体の行を並べ替えました")

        # 6. お届け先電話番号の補完 (需求 4)
        if 'お届け先電話番号' in df_delivery.columns:
            df_delivery['お届け先電話番号'] = df_delivery['お届け先電話番号'].replace(['nan', 'None', ''], pd.NA)
            df_delivery['お届け先電話番号'] = df_delivery['お届け先電話番号'].fillna('048-299-7267')
            process_logs.append("✅ 電話番号の空白を補完しました")

        # --- 処理ロジック終了 ---

    except Exception as e:
        error_occurred = True
        process_logs.append(f"❌ 処理エラー: {str(e)}")

    # --- 処理結果の表示 ---
    st.divider()
    st.subheader("🛠 処理ログ")
    for log in process_logs:
        if "❌" in log: st.error(log)
        else: st.info(log)

    if not error_occurred:
        st.success("🎉 正確に処理が完了しました！ダウンロードしてください。")
        output = io.BytesIO()
        df_delivery.to_csv(output, index=False, encoding='utf-8-sig')
        processed_data = output.getvalue()

        st.download_button(
            label="⬇️ 最終版ファイルをダウンロード",
            data=processed_data,
            file_name="delivery_processed_final.csv",
            mime="text/csv"
        )
else:
    st.info("ファイルをアップロードしてください... 🧡")