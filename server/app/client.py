import streamlit as st
from langserve import RemoteRunnable
from pprint import pprint

st.title('Welcome to Web3Buddy')
input_text = st.text_input('ask web3 related question here')

if input_text:
    with st.spinner("Processing..."):
        try:
            app = RemoteRunnable("http://localhost:8000/web3buddy_chat/", headers={"user_id": "123", "conv_id": "123"})
            for output in app.stream({"input": input_text}):
                for key, value in output.items():
      
                    pprint(f"Node '{key}':")
                     
                pprint("\n---\n")
            output = value['generation']  
            st.write(output)
        
        except Exception as e:
            st.error(f"Error: {e}")