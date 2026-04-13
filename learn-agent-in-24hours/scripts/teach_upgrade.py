from __future__ import annotations
import ast,pathlib,re,textwrap
R=pathlib.Path('.'); L=[p for p in sorted(R.glob('第*小时-*')) if p.is_dir()]
M={'理解最小 Agent':('用纯 Python 规则先搭出 Agent 最小闭环。',['Agent','Tool','Loop','Observation']),'接入真实 LLM':('把假大脑换成真实大模型。',['LLM','System Prompt','API','Fallback']),'手写 ReAct':('显式写出 Thought-Action-Observation 循环。',['ReAct','Thought','Action','Observation']),'函数调用':('用结构化协议描述工具调用。',['Function Calling','Schema','Tool','Validation']),'多工具决策':('让模型在多个工具之间做选择。',['Tool Selection','Tool Chaining','Context','Finish']),'规则系统':('给 Agent 增加行为约束和护栏。',['Rules','Guardrail','Priority','Refusal']),'短期记忆':('让 Agent 记住当前会话里的上下文。',['Memory','Messages','Roles','Replay']),'上下文管理':('在有限窗口里做信息取舍。',['Context Window','Truncation','Summary','Budget']),'LangChain 入门':('第一次用框架接管手写胶水代码。',['LangChain','Tool','Agent','Abstraction']),'LangGraph 入门':('用图来表达节点、边和状态流转。',['Node','Edge','State','Reducer']),'MCP 入门':('理解标准化工具接入协议。',['MCP','Client','Server','Capability']),'自动调研 Agent':('把搜索、筛选和总结串成小型实战流程。',['Research','Source','Scoring','Pipeline']),'Embedding 与向量库':('建立语义向量与相似度检索的直觉。',['Embedding','Vector Store','Similarity','Normalize']),'RAG 基础':('把检索结果接回生成流程。',['Chunking','Retrieve','Augment','Prompt']),'主动检索 Agent':('让 Agent 自己判断何时检索。',['Decision','Retrieval','Context','Answer']),'规划执行':('先拟计划，再分步执行。',['Planning','Dependency','Execution','State']),'反思纠错':('先生成，再审查，再修订。',['Draft','Reflection','Revision','Quality Loop']),'状态持久化':('保存中间状态并支持断点恢复。',['Checkpoint','Resume','State','Recovery']),'Skills 系统':('把能力组织成可注册、可组合的技能模块。',['Skill','Registry','Selection','Modularity']),'多智能体分工':('把任务拆给不同角色协作完成。',['Role','Pipeline','Hand-off','Coordination']),'多智能体编排':('让 supervisor 调度多个角色节点。',['Supervisor','Routing','Shared State','Graph']),'多智能体实战':('把角色、技能和状态合成完整系统。',['Workflow','Contract','Observability','Team']),'Human-in-the-Loop':('把人工审批纳入自动流程。',['Approval','Human-in-the-Loop','Event','Safety']),'部署上线':('把 Agent 包装成可访问服务。',['API','App Factory','Mock/Real','Deployment'])}
N={'run_tool':'统一工具执行入口，便于集中做参数校验、错误处理和日志打印。','fake_brain':'用规则模拟模型决策，帮助你先看懂 Agent 的骨架。','agent_loop':'本章主循环，负责驱动模型、工具和状态更新。','react_loop':'手写 ReAct 的核心循环，反复执行思考、行动和观察。','parse_plan':'把模型文本计划解析成结构化步骤。','parse_react_block':'把模型输出拆成 ReAct 所需字段。','call_model':'负责真正与模型交互，并把结果交回主流程。','build_graph':'定义节点、边和路由关系，是图编排的关键入口。','simulate_without_api':'无 API Key 时的教学降级分支。','run_session':'完整会话驱动器，负责串起消息、工具和结果。','guarded_run_session':'加入规则系统后的会话执行器。','rebuild_messages':'按需要重建下一次模型调用所需消息。','build_agent':'把模型、工具与提示词装配成 Agent。','run_demo':'本章最短可运行演示入口。','mock_search':'教学化搜索函数，用可控数据模拟外部检索。','hash_embedding':'简化版向量函数，用于建立 Embedding 直觉。','cosine_similarity':'通过数学方式比较语义接近程度。','chunk_text':'把长文本切成适合检索的小块。','build_rag_prompt':'把检索结果组织进模型上下文。','rule_based_decide':'用规则决定是否需要检索。','llm_decide':'用模型决定是否需要检索。','build_plan':'把目标拆成可执行步骤。','can_run_step':'检查某步是否满足执行条件。','reflect_answer':'从“有答案”推进到“答案质量是否合格”。','revise_answer':'根据反思意见生成更好的版本。','checkpoint_path':'明确状态落盘位置。','save_checkpoint':'把当前执行状态写到外部介质。','load_checkpoint':'从已保存状态恢复执行。','register_skill':'把技能纳入统一注册表。','pick_skill_with_llm':'让模型承担技能选择层。','planner_agent':'负责先把任务拆清楚。','researcher_agent':'负责收集事实和素材。','writer_agent':'负责把素材组织成对用户可读的输出。','supervisor_node':'调度节点，决定当前轮到谁工作。','_route_supervisor':'根据状态选择下一条执行路径。','run_skill':'统一技能执行入口。','prompt_human_approval':'显式等待人工批准或拒绝。','finalize_release':'批准后再执行最终动作。','create_app':'应用工厂函数，负责组装 API 服务。','main':'脚本入口，通常只负责启动案例。'}
def pick(name):
    for k,v in M.items():
        if k in name: return k,v[0],v[1]
    return name,'围绕这一章主题搭建最小可运行教学案例。',['Concept','Flow','State','Run']

def fn_note(n):
    if n in N: return N[n]
    if n.startswith('tool_'): return '教学工具函数，负责向 Agent 暴露一种可调用能力。'
    if n.startswith('load_'): return '加载配置、数据或环境信息，让主流程保持简洁。'
    if n.startswith('build_'): return '负责组装对象、提示词、索引、图或应用实例。'
    if n.startswith('run_'): return '驱动一段完整流程，把前面准备好的零件真正串起来。'
    if n.startswith('llm_'): return '基于大模型的策略或生成逻辑。'
    if n.startswith('rule_'): return '基于规则的判断或改写逻辑。'
    if n.startswith('mock_'): return '离线教学分支，帮助你在没有外部依赖时也能理解流程。'
    if n.startswith('_'): return '内部辅助函数，为主流程提供局部能力。'
    return '承担本章流程中的一个明确职责，阅读时要关注它的输入、输出和在整条链路中的位置。'

def funcs(p):
    t=p.read_text(encoding='utf-8'); m=ast.parse(t); return [n.name for n in m.body if isinstance(n,ast.FunctionDef)],t

def root_readme():
    return textwrap.dedent('''# 《24小时学会 Agent 开发》\n\n这是一套面向初学者的渐进式 Agent 教材。核心设计思想很简单：每一小时只比上一小时多学一点，这样你既不会一上来就被框架和术语压垮，也不会只会调用黑盒而不知道 Agent 的本质。\n\n## 你会如何学习\n\n- 前 1 到 8 小时：先用手写 Python 建立 Agent 骨架，理解模型、工具、循环、记忆和上下文。\n- 第 9 到 12 小时：开始引入 LangChain、LangGraph、MCP 和一个小型实战项目。\n- 第 13 到 18 小时：进入 Embedding、RAG、主动检索、规划、反思和状态持久化。\n- 第 19 到 24 小时：继续学习 Skills、多智能体、Human-in-the-Loop 和部署上线。\n\n## 为什么建议整仓只维护一份 requirements\n\n建议整套课共享一份 `requirements.txt` 和一个 `.venv` 虚拟环境。这样做对初学者最友好：只安装一次依赖，就能顺着 24 节课一路往后学，不会把大量精力耗在重复配环境上。\n\n## 环境准备\n\n```bash\npython -m venv .venv\npip install -r requirements.txt\n```\n\n把 `.env.example` 复制为 `.env` 后，填入兼容 OpenAI 风格的模型配置：\n\n```bash\nOPENAI_API_KEY=你的密钥\nOPENAI_BASE_URL=https://api.openai.com/v1\nOPENAI_MODEL=gpt-4.1-mini\n```\n\n如果你使用 DeepSeek 一类兼容 OpenAI 协议的服务，只需要把 `OPENAI_BASE_URL` 和 `OPENAI_MODEL` 换成对应值即可。\n\n## 如何运行\n\n```bash\npython run_demo.py --list\npython run_demo.py 1\npython run_demo.py 12\npython run_demo.py 24\n```\n\n也可以直接进入某一章目录：\n\n```bash\ncd "第1小时-理解最小 Agent"\npython src/main.py\n```\n\n## 推荐阅读方式\n\n1. 先看本章 README，弄清楚这一小时新增了什么能力。\n2. 再运行 `src/main.py`，观察中间过程打印。\n3. 对照源码里的文件头注释、函数注释和关键逻辑注释理解实现。\n4. 最后自己改几个参数、提示词、工具或状态结构。\n\n学习 Agent，真正重要的不是背术语，而是逐步建立完整心智模型：`模型 + 工具 + 循环 + 记忆/状态 + 检索/协议 + 编排 + 部署`。\n''')

def lesson_md(folder,fs):
    k,s,cs=pick(folder.name); num=re.search(r'第(\d+)小时',folder.name).group(1)
    items='\n'.join([f'- `{c}`：这是本章必须抓住的关键词，建议你运行代码时带着它去观察程序行为。' for c in cs])
    fmap='\n'.join([f'- `{f}`：{fn_note(f)}' for f in fs])
    return f"# 第 {num} 小时：{k}\n\n## 本章定位\n\n{s}\n\n这是一节面向初学者的渐进式课程。阅读时请先问自己：这一章比上一章究竟多了什么？只有把这个问题答清楚，后面的框架、协议和工程实践才不会变成一堆孤立名词。\n\n## 先建立直觉\n\n你可以把这一章理解成：在上一章已有能力的基础上，再给 Agent 补上一块新的能力拼图。学习重点不是把 API 背下来，而是看清这块拼图在整体系统里处于什么位置、解决什么问题。\n\n## 核心概念\n\n{items}\n\n## 对照源码应该怎么读\n\n本章主代码在 `src/main.py`。建议按下面顺序阅读：\n\n1. 先看文件头注释，建立全局视图。\n2. 再看 `main()`，确认案例是怎么启动的。\n3. 接着找主流程函数，理解这章的执行主线。\n4. 最后回看辅助函数和降级分支，把细节补齐。\n\n### 代码阅读地图\n\n{fmap}\n\n## 新手最容易卡住的点\n\n- 不要只看最终输出，更要看中间的状态变化、工具调用、路由或消息累积。\n- 不要把“能跑”误当成“学会”。你至少应该说得清每个关键函数为什么存在。\n- 如果一时看不懂，先运行案例，再回来对照日志看代码，理解会快很多。\n\n## 建议动手实验\n\n- 修改默认输入，观察流程是否发生变化。\n- 故意改坏一个关键函数，再运行一次，看系统会在哪一步失效。\n- 对照上一章，找出本章新增的代码区域。\n\n## 运行方式\n\n```bash\ncd \"{folder.name}\"\npython src/main.py\n```\n"

def mod_doc(folder):
    k,s,_=pick(folder.name); num=re.search(r'第(\d+)小时',folder.name).group(1)
    return f'"""\n第 {num} 小时：{k}\n\n这份 main.py 是本章对应的最小可运行教学案例。\n\n阅读建议：\n1. 先看 main() 怎么启动案例。\n2. 再看主流程函数如何驱动模型、工具、状态或路由。\n3. 最后再看辅助函数，理解它们分别承担什么职责。\n\n本章新增能力：{s}\n如果你是初学者，建议一边运行一边对照源码，不要只静态阅读。\n"""\n'

def rewrite_code(folder,p,text):
    if text.startswith('"""'):
        i=text.find('"""',3)
        if i!=-1: text=mod_doc(folder)+text[i+3:].lstrip('\r\n')
    else: text=mod_doc(folder)+text
    ls=[]; raw=[x for x in text.splitlines() if not x.startswith('# [教学注释]')]
    i=0
    while i<len(raw):
        line=raw[i]
        if line.startswith('@'):
            ds=[]
            while i<len(raw) and raw[i].startswith('@'): ds.append(raw[i]); i+=1
            if i<len(raw) and re.match(r'^def\s+\w+\s*\(',raw[i]):
                n=re.match(r'^def\s+(\w+)\s*\(',raw[i]).group(1); ls += [f'# [教学注释] `{n}`',f'# {fn_note(n)}','']; ls += ds+[raw[i]]; i+=1; continue
            ls += ds; continue
        if re.match(r'^def\s+\w+\s*\(',line):
            n=re.match(r'^def\s+(\w+)\s*\(',line).group(1); ls += [f'# [教学注释] `{n}`',f'# {fn_note(n)}','',line]; i+=1; continue
        ls.append(line); i+=1
    p.write_text('\n'.join(ls)+'\n',encoding='utf-8')

(R/'README.md').write_text(root_readme(),encoding='utf-8')
for folder in L:
    mp=folder/'src'/'main.py'; rp=folder/'README.md'
    fs,txt=funcs(mp)
    rp.write_text(lesson_md(folder,fs),encoding='utf-8')
    rewrite_code(folder,mp,txt)
