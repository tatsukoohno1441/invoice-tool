import streamlit as st
import pandas as pd
import io

# 页面配置
st.set_page_config(page_title="订单配送处理系统", page_icon="📦")

# --- 【工具插件：超级读取函数】 ---
def secure_read(file):
    """自动尝试不同的编码读取 CSV，且强制所有列为字符串格式"""
    encodings = ['utf-8-sig', 'shift-jis', 'cp932', 'utf-8']
    for enc in encodings:
        try:
            file.seek(0)
            # 【关键更新】：dtype=str 强制所有数据按原样字符串读取，保留前面的0
            df = pd.read_csv(file, encoding=enc, sep=None, engine='python', dtype=str)
            if df.shape[1] > 1:
                return df, f"成功使用 {enc} 编码读取文件"
        except Exception:
            continue
    file.seek(0)
    return pd.read_csv(file, encoding='utf-8-sig', dtype=str), "默认使用 utf-8-sig 读取"

# --- 【主界面】 ---
st.title("订单 & 配送数据自动处理 🧡")
st.write("上传你的两个 CSV 文件，我会自动帮你完成补全、拼接数量、保留编号前导零并导出。")

# 1. 文件上传
col1, col2 = st.columns(2)
with col1:
    order_file = st.file_uploader("上传 Order 文件 (CSV)", type=['csv'])
with col2:
    delivery_file = st.file_uploader("上传 Delivery 文件 (CSV)", type=['csv'])

if order_file and delivery_file:
    process_logs = []
    error_occurred = False

    try:
        # 读取数据
        df_order, order_msg = secure_read(order_file)
        process_logs.append(f"✅ Order 文件: {order_msg}")
        
        df_delivery, delivery_msg = secure_read(delivery_file)
        process_logs.append(f"✅ Delivery 文件: {delivery_msg}")

        # --- 处理逻辑开始 ---

        # 需求 1: 补全 order 文件的 JANコード
        if 'JANコード' in df_order.columns and '商品コード' in df_order.columns:
            # 统一清理空值，保留原样字符串
            df_order['JANコード'] = df_order['JANコード'].replace(['nan', 'None', '<NA>', ''], pd.NA)
            df_order['JANコード'] = df_order['JANコード'].fillna(df_order['商品コード'])
            process_logs.append("✅ 已完成 Order 文件中的 JANコード 补全 (已保留前导零)")

        # 需求 2: 填充 JANコード * 数量 到 delivery 的 品名２ 列
        if all(col in df_order.columns for col in ['注文番号', 'JANコード', '数量']) and '品名２' in df_delivery.columns:
            
            # 按 注文番号 升序
            df_order_sorted = df_order.sort_values(by='注文番号').reset_index(drop=True)
            
            # 处理数量：因为读取时是字符串，这里转为数字进行取整处理，再转回字符
            def format_qty(x):
                try:
                    return str(int(float(x)))
                except:
                    return str(x)
            
            # 拼接 JAN*数量
            combined_list = (
                df_order_sorted['JANコード'] + "*" + df_order_sorted['数量'].apply(format_qty)
            ).tolist()
            
            # 填充到 delivery
            df_delivery['品名２'] = df_delivery['品名２'].astype(object)
            rows_to_fill = min(len(df_delivery), len(combined_list))
            df_delivery.iloc[:rows_to_fill, df_delivery.columns.get_loc('品名２')] = combined_list[:rows_to_fill]
            process_logs.append(f"✅ 已完成 JAN码拼接数量 (例: {combined_list[0] if combined_list else 'N/A'})")
        
        # 需求 3: 排降序
        if '品名２' in df_delivery.columns:
            df_delivery = df_delivery.sort_values(by='品名２', ascending=False)
            process_logs.append("✅ 已按 品名２ 完成降序排列")

        # 需求 4: 电话号码补全
        if 'お届け先電話番号' in df_delivery.columns:
            df_delivery['お届け先電話番号'] = df_delivery['お届け先電話番号'].replace(['nan', 'None', ''], pd.NA)
            df_delivery['お届け先電話番号'] = df_delivery['お届け先電話番号'].fillna('048-299-7267')
            process_logs.append("✅ 已补全空白的 お届け先電話番号")

        # --- 处理逻辑结束 ---

    except Exception as e:
        error_occurred = True
        process_logs.append(f"❌ 处理过程中出现异常: {str(e)}")

    # --- 显示结果界面 ---
    st.divider()
    st.subheader("🛠 处理日志")
    for log in process_logs:
        if "❌" in log: st.error(log)
        elif "⚠️" in log: st.warning(log)
        else: st.info(log)

    if not error_occurred:
        st.success("🎉 处理成功！前导零（如 '00...'）已锁定，不会消失。")
        output = io.BytesIO()
        # 导出时依然保持 utf-8-sig
        df_delivery.to_csv(output, index=False, encoding='utf-8-sig')
        processed_data = output.getvalue()

        st.download_button(
            label="✨ 点击下载最终版 Delivery 文件",
            data=processed_data,
            file_name="processed_delivery_final.csv",
            mime="text/csv"
        )
    else:
        st.error("数据处理未通过，请检查文件。")

else:
    st.info("等待上传文件中... 🧡")