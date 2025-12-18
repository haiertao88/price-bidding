import streamlit as st
import docx
from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import io
import requests
import mistletoe
from mistletoe.base_renderer import BaseRenderer
from mistletoe import block_tokens, span_tokens

# ==========================================
# 部分 1: 核心底层 XML 操作 - 实现完美背景图
# ==========================================
def insert_bg_xml(part, r_id):
    """
    构造 VML XML 代码，用于定义一个铺满全屏的背景图片。
    这是实现真·背景（而非页眉图片）的关键。
    """
    # VML 命名空间定义
    vmldata = f"""<v:background id="_x0000_s1025" o:bwmode="white" fillcolor="white [3212]" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<v:fill r:id="{r_id}" type="frame"/>
</v:background>"""
    bg_element = OxmlElement.from_xml(vmldata)
    part.element.insert(0, bg_element)

def set_true_background(doc, image_stream):
    """
    将图片设置为文档所有章节的真正背景。
    """
    # 获取核心文档部件
    document_part = doc.part
    
    # 将图片添加到文档的关系中，获取其关系 ID (rId)
    # 这一步至关重要，它把图片文件真正存入了 docx 包内
    image_part = document_part.relate_to(image_stream, docx.opc.constants.RELATIONSHIP_TYPE.IMAGE)
    r_id = image_part.rId

    # 遍历所有章节，通常只有一个，但为了保险起见遍历所有
    for section in doc.sections:
        # 获取该章节对应的底层 XML 元素
        section_element = section._sectPr
        # 在底层 XML 中插入背景定义
        insert_bg_xml(section_element, r_id)
        
    # **关键修复**：移除所有页边距。
    # 因为背景图现在是真正的底层背景，不再占用页眉空间。
    # 为了让内容看起来是在背景指定的区域内，需要根据你的背景图设计
    # 在下方的 DocxRenderer 中设置正文的左右缩进。
    # 这里我们先把物理页边距设为较小值，避免 Word 自动排版问题。
    sections = doc.sections
    for section in sections:
        section.top_margin = Cm(2) 
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)


# ==========================================
# 部分 2: 自定义 Markdown 渲染器 (使用 mistletoe)
# ==========================================
class DocxRenderer(BaseRenderer):
    """
    自定义渲染器：将 mistletoe 解析出的 Markdown Token 转换为 docx 操作。
    """
    def __init__(self, doc):
        self.doc = doc
        # 设置正文基础样式 (可选)
        style = doc.styles['Normal']
        font = style.font
        font.name = '微软雅黑'
        font.size = Pt(11)
        super().__init__()

    def render_document(self, token):
        # 遍历文档所有子节点进行渲染
        for child in token.children:
            self.render(child)

    # --- 标题 ---
    def render_heading(self, token):
        level = token.level
        # 获取标题文本
        text = self.render_inner(token)
        # 添加到 docx
        self.doc.add_heading(text, level=level)

    # --- 段落 ---
    def render_paragraph(self, token):
        # 创建新段落
        paragraph = self.doc.add_paragraph()
        # 渲染段落内的具体内容 (可能是普通文本，也可能是粗体、链接等)
        self.render_inner(token, paragraph)

    # --- 普通文本 ---
    def render_raw_text(self, token, parent_paragraph=None):
        if parent_paragraph:
            run = parent_paragraph.add_run(token.content)
            return run
        return token.content

    # --- 粗体/强调 ---
    def render_strong(self, token, parent_paragraph):
        run = self.render_inner(token, parent_paragraph)
        run.bold = True

    def render_emphasis(self, token, parent_paragraph):
        run = self.render_inner(token, parent_paragraph)
        run.italic = True
        
    # --- 列表 ---
    def render_list(self, token):
        # 遍历列表项
        for child in token.children:
            self.render(child, list_style='List Bullet' if not token.start else 'List Number')

    def render_list_item(self, token, list_style):
        # mistletoe 的列表项结构比较深，需要挖掘到具体内容
        if len(token.children) > 0 and isinstance(token.children[0], block_tokens.Paragraph):
             paragraph = self.doc.add_paragraph(style=list_style)
             self.render_inner(token.children[0], paragraph)
        else:
             # 处理复杂列表项，简化处理
             for child in token.children:
                 self.render(child)

    # --- 图片 (核心痛点修复) ---
    def render_image(self, token, parent_paragraph):
        url = token.src
        alt_text = token.title if token.title else (token.children[0].content if token.children else "")
        
        try:
            # 下载网络图片
            # st.write(f"正在下载图片: {url}...") # 调试用
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            image_stream = io.BytesIO(response.content)
            
            # 将图片添加到当前段落
            run = parent_paragraph.add_run()
            run.add_picture(image_stream, width=Cm(15)) # 限制最大宽度，防止撑破
            if alt_text:
                parent_paragraph.add_run(f"\n图注: {alt_text}").italic = True
                
        except Exception as e:
             run = parent_paragraph.add_run(f"[图片下载失败: {alt_text} - URL: {url}]")
             run.font.color.rgb = RGBColor(255, 0, 0)

    # --- 表格 (核心痛点修复) ---
    def render_table(self, token):
        # 计算行数和列数
        rows = len(token.children)
        if rows == 0: return
        # 假设第一行决定列数
        cols = len(token.children[0].children)
        
        # 在 docx 中创建表格
        table = self.doc.add_table(rows=rows, cols=cols)
        table.style = 'Table Grid' # 应用带边框的样式

        # 填充数据
        for i, row_token in enumerate(token.children):
            row = table.rows[i]
            for j, cell_token in enumerate(row_token.children):
                cell = row.cells[j]
                # 清空单元格默认段落
                cell._element.clear_content()
                paragraph = cell.add_paragraph()
                # 渲染单元格内容
                self.render_inner(cell_token, paragraph)

    # 辅助方法：递归渲染内部元素，并传递父级段落对象
    def render_inner(self, token, parent_paragraph=None):
        if hasattr(token, 'children'):
            last_run = None
            for child in token.children:
                # 根据子元素类型调用相应渲染方法
                if isinstance(child, span_tokens.RawText):
                    last_run = self.render_raw_text(child, parent_paragraph)
                elif isinstance(child, span_tokens.Strong):
                    self.render_strong(child, parent_paragraph)
                elif isinstance(child, span_tokens.Emphasis):
                    self.render_emphasis(child, parent_paragraph)
                elif isinstance(child, span_tokens.Image):
                    self.render_image(child, parent_paragraph)
                # ... 可以扩展更多类型 ...
            return last_run # 返回最后一个run用于特定处理，通常不需要
        return token.content


# ==========================================
# 部分 3: Streamlit 主界面逻辑
# ==========================================
st.set_page_config(page_title="高级Markdown转Word", layout="wide", page_icon="📝")

st.title("📝 专业版 Markdown 转 Word (修复背景与格式)")
st.markdown("""
此版本使用了更底层的技术来修复已知问题：
1.  **完美背景**：通过操作 Word 底层 XML，实现真正的全屏背景对齐，消除白边。
2.  **专业解析**：引入了 `mistletoe` 库，支持 Markdown 图片、表格、粗体等复杂格式。
""")
st.warning("注意：为了保证背景图铺满，文档页边距已设置为固定值(上下2cm, 左右2.5cm)。请确保你的背景图设计内容区域在此范围内。")

col1, col2 = st.columns([4, 6])

with col1:
    st.subheader("1. 配置项")
    bg_file = st.file_uploader("上传 A4 背景图 (建议高分辨率 PNG/JPG)", type=['png', 'jpg', 'jpeg'])
    
    st.subheader("3. 执行")
    generate_btn = st.button("🚀 开始高级转换", type="primary", use_container_width=True)

with col2:
    st.subheader("2. 输入 Markdown 内容")
    default_md = """# 公司主要产品介绍

这是一个带有自定义背景的正式文档示例。

## 1. 产品概览图 (测试图片)

下面是一张来自网络的图片，用于测试图片解析功能。

![示例图片](https://via.placeholder.com/600x300/005bb5/ffffff?text=HUAMAI+Product+Image+Test)

## 2. 技术参数表 (测试表格)

我们将使用 Markdown 表格语法来展示数据，测试表格解析功能。

| 指标类别 | 参数说明 | 数值/内容 | 备注 |
| :--- | :--- | :--- | :--- |
| **阻抗** | 标称阻抗 | 50 Ohms | 标准值 |
| **频率范围** | 工作频率 | DC ~ 6 GHz | 宽频带 |
| **VSWR** | 电压驻波比 | ≤ 1.15 (DC~3GHz) | 优异性能 |
| **PIM3** | 三阶互调 | ≤ -160 dBc @2100MHz | 低互调 |
| **耐压** | 证明电压 | 2500 Veff | 海平面 |

## 3. 总结

* **易于使用**：连接方式简便。
* **高性能**：各项指标均达到行业领先水平。

> 注：此文档由自动化工具生成。
"""
    md_input = st.text_area("在此粘贴内容 (支持图片URL和表格)", height=600, value=default_md)

if generate_btn:
    if not md_input.strip():
        st.error("请输入 Markdown 内容！")
    else:
        with st.spinner("正在进行复杂的 XML 处理和 Markdown 解析，请稍候..."):
            try:
                # 1. 初始化文档
                doc = Document()
                
                # 2. 应用真·背景图 (如果上传了)
                if bg_file:
                    # 读取图片流
                    image_stream = io.BytesIO(bg_file.getvalue())
                    # 调用底层 XML 处理函数
                    set_true_background(doc, image_stream)
                    # st.success("已应用底层 XML 背景图技术。")

                # 3. 使用自定义渲染器解析 Markdown
                renderer = DocxRenderer(doc)
                # mistletoe 将 markdown 文本转换为 token 树，然后传入渲染器
                doc_token = mistletoe.Document(md_input)
                renderer.render(doc_token)
                
                # 4. 保存结果到内存
                doc_io = io.BytesIO()
                doc.save(doc_io)
                doc_io.seek(0)
                
                st.success("✅ 文档生成成功！")
                # 5. 提供下载
                st.download_button(
                    label="📥 下载最终版 .docx 文件",
                    data=doc_io,
                    file_name="Advanced_Generated_Doc.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary"
                )
                
            except Exception as e:
                st.error(f"生成过程中发生错误:\n{str(e)}")
                import traceback
                st.expander("查看详细错误信息").code(traceback.format_exc())
