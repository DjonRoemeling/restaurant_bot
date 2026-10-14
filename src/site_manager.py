import streamlit as st
from main import caca

st.title("Restaurant recommendation system")
if "messages" not in st.session_state:
    st.session_state.messages = []
if "responses" not in st.session_state:
    st.session_state.responses= []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

input_user =st.chat_input("Hello, welcome to the Cambridge restaurant recommendation system. How may I help you?")
if input_user:  
    st.chat_message("user").markdown(input_user)
    st.session_state.messages.append({"role": "user", "content": input_user})


    with st.chat_message("assistant"):
        bot_resp = caca(input_user)

     
        if bot_resp is not None:
            st.write(bot_resp)

    st.session_state.messages.append({"role": "assistant", "content": input_user})

    st.rerun()


