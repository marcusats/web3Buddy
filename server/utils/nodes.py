from document import Document
from utils.generate_chain import create_generate_chain
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import PromptTemplate
import subprocess
import time
import json
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv()) 
infura_key = os.getenv("INFURA_API_KEY")

class GraphNodes:
    def __init__(self, llm, retriever, retrieval_grader, hallucination_grader, code_evaluator, question_rewriter, saveMessage,get_all_messages):
        self.llm = llm
        self.retriever = retriever
        self.retrieval_grader = retrieval_grader
        self.hallucination_grader = hallucination_grader
        self.code_evaluator = code_evaluator
        self.question_rewriter = question_rewriter
        self.generate_chain = create_generate_chain(llm)
        self.userId = ""
        self.conv_id = ""
        self.saveMessage = saveMessage
        self.get_all_messages = get_all_messages
    
    def saveChatInfo(self, userId, conv_id):
        """
        Save the userId from the state to the graph.

        Args:
            state (dict): The current graph state

        Returns:
            dict: Updated state with the userId.
        """
        print("---SAVE USER ID---")
        self.userId = userId
        self.conv_id = conv_id 


    def rewrite_question(self, state):
        """
        Rewrites the input question to optimize it for vector store retrieval and tool usage.

        Args:
            state (dict): The current graph state

        Returns:
            dict: Updated state with the rewritten question.
        """
        print("---REWRITE QUESTION---")
        question = state["input"]
        
        
        
        self.saveMessage(self.userId, self.conv_id, question, "user")
        chat_history = state.get("chat_history", [])
        print("----------CHAT HISTORY----------")
        print(f"context: {chat_history}")
        print("----------User----------")
        print(f"userId: {self.userId}")
        print(f"conv_id: {self.conv_id}")
        if not chat_history:
            chat_history = self.get_all_messages(self.userId, self.conv_id)

        # Create a prompt for rewriting the question
        rewrite_prompt = PromptTemplate(
            template="""
            <|begin_of_text|><|start_header_id|>system<|end_header_id|>
            Your task is to improve the clarity and precision of the user's question without altering its original intent.
            Do not add any new information or change the meaning of the question. 
            Only rewrite the question itself.

            The question to be rewritten is below:
            "{question}"

            <|eot_id|>
            <|start_header_id|>user<|end_header_id|>
            Please rewrite the question to be more clear and concise, while keeping its original intent intact.
            <|eot_id|>
            <|start_header_id|>assistant<|end_header_id|>
            """,
            input_variables=["question"]
        )

        # Invoke the question rewriter
        
        question_rewriter =  rewrite_prompt | self.llm | StrOutputParser()
        rewritten_question = question_rewriter.invoke({"question": question})
        print(f"Rewritten Question: {rewritten_question}")

        # Update the state with the rewritten question
       # Store the rewritten question as 'generation'

        return {
            "chat_history": chat_history,
            "input": question,  # Update input with rewritten question
            "documents": [],
            "generation": rewritten_question,
            "userId": self.userId,
            "convId": self.conv_id
        }

    def chat(self, state):
        """
        A chat node to handle conversational interactions using historical context and document retrieval.
        It ensures that the LLM uses retrieved documents to avoid hallucination.
        """
        print("---CHAT---")
        question = state["input"]
        chat_history = state.get("chat_history", [])
        print(f"userId: {state['userId']}")

        def create_system_prompt(chat_history, input):
            return (
                "You are Web3Buddy, a helpful assistant that provides detailed answers about Web3. "
                "Always refer to the context from the previous conversation and the following retrieved documents. "
                "Do not make up any information; if the documents do not have enough details, say you don't know. "
                "You have access to tools, including 'fake_weather_api' to check the weather and a tool to 'generate_infura_data' information about Infura.\n\n"
                f"Chat History:\n{chat_history}\n\n"
                
                f"Question: {input}\n\n"
            )

        system_prompt = create_system_prompt(chat_history, question)
        
        
        
        # Combine the chat prompt with the LLM and output parser
        response = self.llm.invoke(system_prompt)

        # Ensure the response is properly serialized into a string
        # if isinstance(response, dict):
        #      # Convert dictionary response to JSON string for serialization
        # elif not isinstance(response, str):
        #     response = str(response)  # Convert to string if not already
        
        print("---CHAT RESPONSE---")
        print( response)
        # Append the question and AI response to the chat history
        chat_history.append(HumanMessage(content=question))
        chat_history.append(response)  # Add the serialized string response

        # Store the response as 'generation'
        state['generation'] = response  # Store serialized response in the 'generation' key
        state['chat_history'] = chat_history  # Update chat history
        
        

        return {
            "chat_history": chat_history,
            "input": question,
            "documents": [],
            "generation": response.content  
        }

    def retrieveInfura(self, state):
        """
        Retrieve documents from the vector store based on the user's query.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, 'documents', that contains retrieved documents
        """
        print("---RETRIEVE---")
        improvedQuestion = state["input"]
     
        # Retrieval
        print(f"Improved Question: {improvedQuestion}")
       
        infura_retriver = self.retriever.get_retriever()
        documents = infura_retriver.invoke(improvedQuestion)
        print("---RETRIEVED DOCUMENTS---")
        print(documents)
        return {"documents": documents, "input": improvedQuestion, "vector_store_namespace": "infura-docs"}
    
    def retrieveSolidity(self, state):
        """
        Retrieve documents from the vector store based on the user's query.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, 'documents', that contains retrieved documents
        """
        print("---RETRIEVE---")
        improvedQuestion = state["input"]
     
        # Retrieval
        print(f"Improved Question: {improvedQuestion}")

        new_namespace = "solidity-docs"
        changed_retriever = self.retriever.set_namespace(new_namespace)
        solidity_retriver = self.retriever.get_retriever()
        documents = solidity_retriver.invoke(improvedQuestion)
        print("---RETRIEVED DOCUMENTS---")
        print(documents)
        return {"documents": documents, "input": improvedQuestion, "vector_store_namespace": new_namespace}


    def generate(self, state):
        """
        Generate an answer using LLM based on retrieved documents and the question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, 'generation', that contains LLM generation
        """
        print("---GENERATE---")
        question = state["input"]
        documents = state["documents"]

        # RAG generation
        generation = self.generate_chain.invoke({"context": documents, "input": question})
        return {"documents": documents, "input": question, "generation": generation}

    def grade_documents(self, state):
        """
        Determines whether the retrieved documents are relevant to the question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates 'documents' key with only filtered relevant documents
        """
        print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
        question = state["input"]
        documents = state["documents"]
        print(f"Question: {question}")
        print(f"Documents: {documents}")

        # Score each document
        filtered_docs = []
        for d in documents:
            score = self.retrieval_grader.invoke({"input": question, "document": d.page_content})
            grade = score["score"]
            if grade == "yes":
                print("---GRADE: DOCUMENT RELEVANT---")
                filtered_docs.append(d)
            else:
                print("---GRADE: DOCUMENT IRRELEVANT---")
                continue

        return {"documents": filtered_docs, "input": question}

    def transform_query(self, state):
        """
        Transform the query to produce a better question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates 'input' key with a re-phrased question
        """
        print("---TRANSFORM QUERY---")
        question = state["input"]
        documents = state["documents"]

        # Re-write question
        better_question = self.question_rewriter.invoke({"question": question})
        return {"documents": documents, "input": better_question}
    
    def transform_execution(self, state):
        """
        Transforms the 'generation' (interpretation of the documentation with an answer) 
        and 'input' (the question) into an executable cURL command.

        Args:
            state (dict): The current graph state, containing 'generation' (the interpreted answer) and 'input' (the question).

        Returns:
            dict: Updated state with the extracted cURL command.
        """
        print("---TRANSFORM EXECUTION---")
        
        # Retrieve the question (input) and the interpreted answer (generation)
        question = state["input"]
        generation = state["generation"]
        
        # Define a prompt that extracts the cURL command
        transform_prompt = PromptTemplate(
            template="""
            <|begin_of_text|><|start_header_id|>system<|end_header_id|>
            You are tasked with extracting only the cURL command from a given block of text.
            
            The extracted cURL command should not contain any Markdown formatting or explanation text, 
            and it must be fully executable in a terminal. Ensure the following:

            - Remove any "```bash" or similar Markdown notation.
            - Replace any mentions of API keys with `infuraKey` within curly brakets to be replaced later.
            - Provide only the clean cURL command, no additional information.

            Below is the text from which to extract the cURL command:
            {generation}

            <|eot_id|>
            <|start_header_id|>user<|end_header_id|>
            Ensure only the cURL command is returned without any surrounding Markdown notation or extra explanation.
            The placeholder for the API key should be replaced with `infuraKey` within curly brakets .
            <|eot_id|>
            <|start_header_id|>assistant<|end_header_id|>
            """,
            input_variables=["generation"]
        )
        
        # Invoke the transformation prompt to extract the cURL command
        extract_command = transform_prompt | self.llm | StrOutputParser()
        curl_command = extract_command.invoke({"generation": generation})

        print(f"Extracted cURL Command: {curl_command}")

        # Ensure that the extracted cURL command has no Markdown or unnecessary info
        curl_command_cleaned = curl_command.replace("```bash", "").replace("```", "").strip()

        # Update the state with the cleaned cURL command
        state["generation"] = curl_command_cleaned  # Store the cleaned cURL command as 'generation'

        return {
            "chat_history": state.get("chat_history", []),
            "input": question,  # Keep the original input question
            "documents": state.get("documents", []),
            "generation": curl_command_cleaned  # Store the cleaned cURL command
        }
    
    def execution(self, state):
        """
        Executes the cURL command extracted from the generation, inserts the Infura key, and returns the command output.
        Retries up to 3 times in case of failure or timeout, and returns an error message if unsuccessful.

        Args:
            state (dict): The current graph state, containing 'generation' (the cURL command).

        Returns:
            dict: Updated state with the result of the cURL command execution or an error message.
        """
        print("---EXECUTING CURL COMMAND---")
        
        # Retrieve the cURL command from the generation
        curl_command = state["generation"]

        # Replace the placeholder {infuraKey} with the actual Infura key
        curl_command_with_key = curl_command.replace("{infuraKey}", infura_key)

        # Print the command to be executed for debugging
        print(f"Executing: {curl_command_with_key}")

        print(f"user id: {state['userId']}")
        # Define max retries and delay between retries
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                # Execute the command using subprocess with a timeout of 10 seconds
                result = subprocess.run(curl_command_with_key, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
                
                # Capture the output
                command_output = result.stdout.decode('utf-8')
                print(f"Command Output: {command_output}")
                
                # Update the state with the output of the command
                state["generation"] = command_output

                return {
                    "chat_history": state.get("chat_history", []),
                    "input": state["input"],  # Keep the original input question
                    "documents": state.get("documents", []),
                    "generation": command_output  # Store the output in the generation key
                }
            
            except subprocess.TimeoutExpired:
                print(f"Attempt {attempt+1}: Timeout occurred while executing the command.")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)  # Wait before retrying
                else:
                    print("Max retries reached. Service unavailable.")
                    error_message = f"Service for this {curl_command_with_key} is currently unavailable due to a timeout."
                    return self._return_error(state, error_message)
            
            except subprocess.CalledProcessError as e:
                error_message = e.stderr.decode('utf-8')
                print(f"Attempt {attempt+1}: Error executing cURL command: {error_message}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)  # Wait before retrying
                else:
                    print("Max retries reached. Service unavailable.")
                    error_message = f"Service for this {curl_command_with_key} is currently unavailable."
                    return self._return_error(state, error_message)

    def _return_error(self, state, error_message):
        """
        Helper function to handle returning error messages.

        Args:
            state (dict): The current graph state.
            error_message (str): The error message to return.

        Returns:
            dict: Updated state with the error message.
        """
        print(f"Returning error: {error_message}")
        
        # Update the state with the error message
        

        return {
            "chat_history": state.get("chat_history", []),
            "input": state["input"],  # Keep the original input question
            "documents": state.get("documents", []),
            "generation": error_message  # Store the error message in the generation key
        }

    def path_to_execution(self, state):
        """
        This function guides the process towards potential execution.

        Args:
            state (dict): The current graph state

        Returns:
            dict: The updated state indicating the next steps.
        """
        print("---Guiding to probable execution---")
        return {
            "chat_history": state.get("chat_history", []),
            "input": state.get("input"),
            "documents": state.get("documents", []),
            "generation": state.get("generation"),
        
        }
    
    def execution_interpreter(self, state):
        """
        Interprets the output of the cURL command execution and provides a concise response.
        If the result contains hexadecimal values, it converts them to human-readable numbers.

        Args:
            state (dict): The current graph state, containing 'generation' (the command output).

        Returns:
            dict: Updated state with the interpretation of the command output.
        """
        print("---Interpreting Execution Output---")
        
        # Retrieve the output of the cURL command execution
        command_output = state["generation"]
        documents = state.get("documents", [])
        input_question = state["input"]

        # Define a prompt that interprets the command output concisely and converts hex to human-readable numbers
        interpret_prompt = PromptTemplate(
            template="""
            <|begin_of_text|><|start_header_id|>system<|end_header_id|>
            Your task is to interpret the output of the cURL command execution and provide a clear response explaning what this command result means.
            If there are any hexadecimal values in the "result" field (e.g., "0x497c5d178"), convert them to human-readable decimal numbers and explain their significance.
            Provide only the most relevant interpretation of the output, including any errors if present. Make sure that in the answer you show the command used and the output, then explain.

            The output of the cURL command execution is below:
            {generation}
            
            The question that led to this command execution is: {input}

            Additionally, consider the following documents which may provide context:
            {documents}
            
            <|eot_id|>
            <|start_header_id|>user<|end_header_id|>
            Please interpret the output of the cURL command execution. Convert any hexadecimal values to human-readable numbers.
            <|eot_id|>
            <|start_header_id|>assistant<|end_header_id|>
            """,
            input_variables=["generation", "documents", "input"]  # Include the input question for context
        )
        
        # Invoke the interpretation prompt to analyze the command output and handle hex conversions
        interpretation = interpret_prompt | self.llm | StrOutputParser()
        interpretation_output = interpretation.invoke({"generation": command_output, "documents": documents, "input": input_question})

        print(f"Interpreted Output: {interpretation_output}")

        return {
                "chat_history": state.get("chat_history", []),
                "input": state.get("input"),
                "documents": state.get("documents", []),
                "generation": interpretation_output,
        }
    
    def ending(self, state):
        """
        The final node in the graph that ends the conversation.

        Args:
            state (dict): The current graph state

        Returns:
            dict: The final state indicating the end of the conversation.
        """
        print("---END---")
        print(f"documents: {state['documents']}")
        print(f"userId: {state['userId']}")
        print(f"conv_id: {state['convId']}")
        print(f"generation: {state['generation']}")
        print(f"chat_history: {state['chat_history']}")
        print(f"input: {state['input']}")

        
     
        self.saveMessage(state["userId"], state["convId"], state["generation"], "assistant")

        return {
            "chat_history": state.get("chat_history", []),
            "input": state.get("input"),
            "documents": state.get("documents", []),
            "generation": state.get("generation"),
        }

