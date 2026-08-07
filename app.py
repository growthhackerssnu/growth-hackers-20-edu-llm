"""데모 사이트. 수정하지 마세요.

  streamlit run app.py
"""

import streamlit as st

import agent

st.set_page_config(page_title="여행 일정 에이전트", page_icon="🧳")
st.title("🧳 여행 일정 에이전트")
st.caption(f"model: {agent.MODEL} · tools: {', '.join(agent.TOOLS) or '(없음 — tools.py 를 채우세요)'}")

if "history" not in st.session_state:
    st.session_state.history = []

for m in st.session_state.history:
    st.chat_message(m["role"]).write(m["content"])

if prompt := st.chat_input("어디로, 며칠 동안 가시나요?"):
    st.chat_message("user").write(prompt)
    answer = ""
    with st.chat_message("assistant"):
        for ev in agent.run(prompt, st.session_state.history):
            if ev[0] == "tool":
                with st.expander(f"🔧 {ev[1]}"):
                    st.json(ev[2])
                    st.code(ev[3])
            else:
                answer = ev[1]
                st.markdown(answer)
    st.session_state.history += [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": answer},
    ]
