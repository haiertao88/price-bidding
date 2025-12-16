import streamlit as st
import pandas as pd
import io

# --- 页面配置 ---
st.set_page_config(page_title="供应商比价系统", layout="centered")

# --- 模拟数据库 (注意：免费版重启后数据会重置，请及时导出Excel) ---
if 'data' not in st.session_state:
    st.session_state.data = {
        '光纤连接器 Type-A': {'min': 100.0, 'max': 120.0, 'bids': []},
        '路由器外壳 CNC': {'min': 50.0, 'max': 60.0, 'bids': []},
        '5G 基站散热片': {'min': 200.0, 'max': 210.0, 'bids': []}
    }

# --- 登录逻辑 ---
def login_page():
    st.title("🔐 供应商竞价系统登录")
    
    with st.form("login_form"):
        username = st.text_input("账号 (供应商/管理员)")
        password = st.text_input("密码", type="password")
        submitted = st.form_submit_button("登录")
        
        if submitted:
            # 这里设置简单的账号密码
            if username == "admin" and password == "admin888":
                st.session_state.user_type = "admin"
                st.session_state.user = username
                st.rerun()
            elif username in ["supA", "supB", "supC"] and password == "123":
                st.session_state.user_type = "supplier"
                st.session_state.user = username
                st.rerun()
            else:
                st.error("账号或密码错误！(测试用: admin/admin888, supA/123)")

# --- 供应商界面 ---
def supplier_dashboard():
    st.sidebar.title(f"👤 供应商: {st.session_state.user}")
    if st.sidebar.button("退出登录"):
        st.session_state.clear()
        st.rerun()

    st.title("📊 实时报价大厅")
    st.info("提示：你能看到当前的最低和最高价，但看不到是谁报的。")

    for product_name, info in st.session_state.data.items():
        with st.container():
            st.markdown(f"### 📦 {product_name}")
            col1, col2, col3 = st.columns([1, 1, 2])
            
            # 显示盲拍价格
            col1.metric("当前最低价", f"¥{info['min']}", delta_color="inverse")
            col2.metric("当前最高价", f"¥{info['max']}")
            
            # 报价输入区
            with col3:
                with st.form(key=product_name):
                    new_price = st.number_input("输入你的报价", min_value=0.0, step=0.1, label_visibility="collapsed")
                    if st.form_submit_button("🚀 提交报价"):
                        if new_price > 0:
                            # 记录数据
                            info['bids'].append({
                                'supplier': st.session_state.user,
                                'price': new_price,
                                'time': pd.Timestamp.now().strftime('%H:%M:%S')
                            })
                            # 更新极值
                            all_prices = [b['price'] for b in info['bids']]
                            # 包含初始值计算
                            if info['min'] == 0: info['min'] = new_price
                            info['min'] = min(all_prices + [info['min']])
                            info['max'] = max(all_prices + [info['max']])
                            
                            st.success(f"已提交: ¥{new_price}")
                            st.rerun()
            st.divider()

# --- 管理员界面 (甲方看这个) ---
def admin_dashboard():
    st.sidebar.title("👮‍♂️ 管理员模式")
    if st.sidebar.button("退出登录"):
        st.session_state.clear()
        st.rerun()

    st.title("📋 报价总览 (甲方)")

    # 1. 导出 Excel 功能
    all_records = []
    for pname, info in st.session_state.data.items():
        for bid in info['bids']:
            all_records.append({
                '产品': pname,
                '供应商': bid['supplier'],
                '价格': bid['price'],
                '时间': bid['time']
            })
    
    if all_records:
        df = pd.DataFrame(all_records)
        st.dataframe(df, use_container_width=True)
        
        # 生成 Excel 下载链接
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='报价单')
            
        st.download_button(
            label="📥 下载 Excel 报价单",
            data=buffer.getvalue(),
            file_name="suppliers_bids.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:
        st.warning("暂无报价数据")

# --- 主程序逻辑 ---
if 'user' not in st.session_state:
    login_page()
else:
    if st.session_state.user_type == "admin":
        admin_dashboard()
    else:
        supplier_dashboard()