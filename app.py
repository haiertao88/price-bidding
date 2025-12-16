import streamlit as st
import pandas as pd
import io

# --- 页面配置 ---
st.set_page_config(page_title="供应商比价系统", layout="centered")

# ==========================================
# 核心修改：使用 @st.cache_resource 实现全局共享
# 这样所有人看到的都是同一份数据！
# ==========================================
@st.cache_resource
def get_global_data():
    # 返回一个字典，充当全局数据库
    return {
        # 预设几个产品，避免空空如也
        '光纤连接器 Type-A': {'bids': []},
        '路由器外壳 CNC': {'bids': []}
    }

# 获取全局数据对象 (注意：这里不用 session_state 了)
shared_data = get_global_data()

# --- 辅助功能：计算排名 ---
def get_product_rankings(product_name):
    if product_name not in shared_data:
        return []
        
    bids = shared_data[product_name]['bids']
    if not bids:
        return []
    
    # 逻辑：每个供应商取最低价
    supplier_best = {}
    for bid in bids:
        sup = bid['supplier']
        price = bid['price']
        if sup not in supplier_best or price < supplier_best[sup]['price']:
            supplier_best[sup] = bid

    # 排序：价格从低到高
    ranked_list = sorted(supplier_best.values(), key=lambda x: x['price'])
    return ranked_list

# --- 登录逻辑 (保持不变) ---
def login_page():
    st.title("🔐 供应商竞价系统登录")
    with st.form("login_form"):
        username = st.text_input("账号")
        password = st.text_input("密码", type="password")
        submitted = st.form_submit_button("登录")
        
        if submitted:
            if username == "admin" and password == "admin888":
                st.session_state.user_type = "admin"
                st.session_state.user = username
                st.rerun()
            elif username in ["supA", "supB", "supC"] and password == "123":
                st.session_state.user_type = "supplier"
                st.session_state.user = username
                st.rerun()
            else:
                st.error("账号或密码错误！")

# --- 供应商界面 (读取 shared_data) ---
def supplier_dashboard():
    current_user = st.session_state.user
    st.sidebar.title(f"👤 供应商: {current_user}")
    
    # 强制刷新按钮 (因为是全局数据，有时需要手动刷新看最新状态)
    if st.sidebar.button("🔄 刷新最新排名"):
        st.rerun()
        
    if st.sidebar.button("退出登录"):
        st.session_state.clear()
        st.rerun()

    st.title("📊 实时报价大厅")

    if not shared_data:
        st.info("👋 甲方暂未发布任何询价产品。")
        return

    for product_name in list(shared_data.keys()): # 使用 list() 避免遍历时修改报错
        info = shared_data[product_name]
        with st.container():
            st.markdown(f"### 📦 {product_name}")
            
            rankings = get_product_rankings(product_name)
            min_price = rankings[0]['price'] if rankings else 0
            
            # 计算我的排名
            my_rank = None
            my_best_price = None
            
            for idx, rank_info in enumerate(rankings):
                if rank_info['supplier'] == current_user:
                    my_rank = idx + 1
                    my_best_price = rank_info['price']
                    break
            
            # 显示数据
            col1, col2, col3 = st.columns([1, 1, 2])
            col1.metric("全场最低价", f"¥{min_price}" if min_price else "--")
            
            if my_rank == 1:
                col2.metric("我的排名", "第 1 名 🏆", delta="当前领先", delta_color="normal")
            elif my_rank:
                diff = my_best_price - min_price
                col2.metric("我的排名", f"第 {my_rank} 名", delta=f"落后 ¥{diff:.2f}", delta_color="inverse")
            else:
                col2.metric("我的排名", "未报价")

            # 报价表单
            with col3:
                with st.form(key=f"form_{product_name}"):
                    new_price = st.number_input("输入报价", min_value=0.0, step=1.0, label_visibility="collapsed")
                    if st.form_submit_button("🚀 提交报价"):
                        if new_price > 0:
                            # --- 关键修改：写入全局 shared_data ---
                            shared_data[product_name]['bids'].append({
                                'supplier': current_user,
                                'price': new_price,
                                'time': pd.Timestamp.now().strftime('%H:%M:%S')
                            })
                            st.success("报价成功！")
                            st.rerun()
            st.divider()

# --- 管理员界面 (读取 shared_data) ---
def admin_dashboard():
    st.sidebar.title("👮‍♂️ 管理员模式")
    if st.sidebar.button("🔄 刷新数据"):
        st.rerun()
    if st.sidebar.button("退出登录"):
        st.session_state.clear()
        st.rerun()

    st.title("📋 甲方总控台")
    
    tab1, tab2, tab3 = st.tabs(["🏆 实时排名", "⚙️ 产品管理", "📝 历史记录"])

    # Tab 1: 排名
    with tab1:
        if not shared_data:
            st.info("暂无产品。")
        for p_name in shared_data.keys():
            st.subheader(f"📦 {p_name}")
            rankings = get_product_rankings(p_name)
            if rankings:
                rank_data = [{"排名": f"第 {i+1} 名", "供应商": r['supplier'], "价格": r['price'], "时间": r['time']} for i, r in enumerate(rankings)]
                st.table(rank_data)
            else:
                st.caption("等待报价...")
            st.divider()

    # Tab 2: 管理
    with tab2:
        st.header("发布/删除产品")
        with st.form("add_product"):
            new_name = st.text_input("新产品名称")
            if st.form_submit_button("➕ 发布"):
                if new_name and new_name not in shared_data:
                    shared_data[new_name] = {'bids': []}
                    st.success(f"已发布: {new_name}")
                    st.rerun()
        
        st.divider()
        for p_name in list(shared_data.keys()):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**{p_name}**")
            if c2.button("🗑️ 删除", key=f"del_{p_name}"):
                del shared_data[p_name]
                st.rerun()

    # Tab 3: 导出
    with tab3:
        all_records = []
        for pname, info in shared_data.items():
            for bid in info['bids']:
                all_records.append({'产品': pname, '供应商': bid['supplier'], '价格': bid['price'], '时间': bid['time']})
        
        if all_records:
            df = pd.DataFrame(all_records)
            st.dataframe(df, use_container_width=True)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 导出Excel", buffer.getvalue(), "bids.xlsx")
        else:
            st.warning("暂无数据")

# --- 主程序 ---
if 'user' not in st.session_state:
    login_page()
else:
    if st.session_state.user_type == "admin":
        admin_dashboard()
    else:
        supplier_dashboard()
