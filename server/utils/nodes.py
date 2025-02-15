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

        question_rewriter =  rewrite_prompt | self.llm | StrOutputParser()
        rewritten_question = question_rewriter.invoke({"question": question})
        print(f"Rewritten Question: {rewritten_question}")

        return {
            "chat_history": chat_history,
            "input": question,
            "documents": [],
            "generation": question,
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

                f"Chat History:\n{chat_history}\n\n"
                
                f"Question: {input}\n\n"
            )

        system_prompt = create_system_prompt(chat_history, question)
        
        response = self.llm.invoke(system_prompt)

        print("---CHAT RESPONSE---")
        print( response)
        chat_history.append(HumanMessage(content=question))
        chat_history.append(response)

        state['generation'] = response
        state['chat_history'] = chat_history
        
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
     
        print(f"Improved Question: {improvedQuestion}")
        new_namespace = "infura-docs"
        changed_retriever = self.retriever.set_namespace(new_namespace)
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
        generation = state.get("generation", "")
        print(f"Question: {question}")
        print(f"Documents: {documents}")

        filtered_docs = []
        for d in documents:
            score = self.retrieval_grader.invoke({"input": question, "document": d.page_content, "rewrited_question":generation } )
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
        print("-----transform query-----")

        better_question = self.question_rewriter.invoke({"question": question})
        print(f"Better Question: {better_question}")
        return {"documents": documents, "input": question, "generation": better_question}
    
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
        
        question = state["input"]
        generation = state["generation"]
        
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
        
        extract_command = transform_prompt | self.llm | StrOutputParser()
        curl_command = extract_command.invoke({"generation": generation})

        print(f"Extracted cURL Command: {curl_command}")

        curl_command_cleaned = curl_command.replace("```bash", "").replace("```", "").strip()

        state["generation"] = curl_command_cleaned

        return {
            "chat_history": state.get("chat_history", []),
            "input": question,
            "documents": state.get("documents", []),
            "generation": curl_command_cleaned
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
        
        curl_command = state["generation"]

        curl_command_with_key = curl_command.replace("{infuraKey}", infura_key)

        print(f"Executing: {curl_command_with_key}")

        print(f"user id: {state['userId']}")
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                result = subprocess.run(curl_command_with_key, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
                
                command_output = result.stdout.decode('utf-8')
                print(f"Command Output: {command_output}")
                
                state["generation"] = command_output

                return {
                    "chat_history": state.get("chat_history", []),
                    "input": state["input"],
                    "documents": state.get("documents", []),
                    "generation": command_output
                }
            
            except subprocess.TimeoutExpired:
                print(f"Attempt {attempt+1}: Timeout occurred while executing the command.")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print("Max retries reached. Service unavailable.")
                    error_message = f"Service for this {curl_command_with_key} is currently unavailable due to a timeout."
                    return self._return_error(state, error_message)
            
            except subprocess.CalledProcessError as e:
                error_message = e.stderr.decode('utf-8')
                print(f"Attempt {attempt+1}: Error executing cURL command: {error_message}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
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
        
        return {
            "chat_history": state.get("chat_history", []),
            "input": state["input"],
            "documents": state.get("documents", []),
            "generation": error_message
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
        
        command_output = state["generation"]
        documents = state.get("documents", [])
        input_question = state["input"]

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
            input_variables=["generation", "documents", "input"]
        )
        
        interpretation = interpret_prompt | self.llm | StrOutputParser()
        interpretation_output = interpretation.invoke({"generation": command_output, "documents": documents, "input": input_question})

        print(f"Interpreted Output: {interpretation_output}")

        return {
                "chat_history": state.get("chat_history", []),
                "input": state.get("input"),
                "documents": state.get("documents", []),
                "generation": interpretation_output,
        }
    
    def params_needed(self, state):
        """
        Guides the workflow into the 'params needed' conditional edge by analyzing the cURL command 
        and identifying which parameters are required for its execution.

        Args:
            state (dict): The current graph state, containing the cURL command, related documents, and the user's input question.

        Returns:
            dict: The updated state indicating the parameters needed for the cURL command, with parameter names and types.
        """
        
        print("---PARAMS NEEDED---")
        return {
            "chat_history": state.get("chat_history", []),
            "input": state.get("input"),
            "documents": state.get("documents", []),
        }
    def params_inquiry(self, state):
        """ 
        Inquires about the missing parameters for the cURL command execution.

        Args:
            state (dict): The current graph state, containing the cURL command, related documents, and the user's input question.

        Returns:
            dict: The updated state indicating the parameters needed for the cURL command, with parameter names and types.

        """
        command_output = state["generation"]
        documents = state.get("documents", [])
        input_question = state["input"]

        interpret_prompt = PromptTemplate(
            template="""
            <|begin_of_text|><|start_header_id|>system<|end_header_id|>
            Your task is to analyze the provided cURL command and identify which parameters are required for its execution. 
            Specifically, you will:
            
            1. Review the cURL command and check if there is a method call (e.g., "eth_call").
            2. Identify if parameters such as `address`, `block`, or others are required based on the method call.
            3. Review the provided documents to see if the method mentioned in the cURL command has any specific parameters that are necessary.
            4. Provide a structured response in the following format:
            
            {{
            "input": "{input_question}",                # The question or input that led to the cURL command
            "content": "A brief description of the needed parameters",  # Explanation of the parameters
            "params": {{
                "param_name_1": "param_type_1",         # Param name and type (string, bool, int, etc.)
                "param_name_2": "param_type_2"
            }}
            }}
            
            DO NOT ADD MARKDOWN NOTATION ```json , PLAIN OBJECT 
            The cURL command is provided below:
            {generation}

            The question that led to this cURL command is: {input_question}

            Additionally, consider the following documents which may provide context:
            {documents}

            Ignore any references to API keys and focus only on relevant execution parameters such as `address`, `block`, `data`, etc.

            <|eot_id|>
            <|start_header_id|>user<|end_header_id|>
            Please analyze the cURL command, check for method calls, and identify the required parameters for execution. Provide the structured response with parameter names and types.
            <|eot_id|>
            <|start_header_id|>assistant<|end_header_id|>
            """,
            input_variables=["generation", "documents", "input_question"]
        )

        interpretation = interpret_prompt | self.llm | StrOutputParser()

        interpretation_output = interpretation.invoke({
            "generation": command_output, 
            "documents": documents, 
            "input_question": input_question
        })

        print("---PARAMS INQUIRY---")
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
    
    def adding_params(self, state):
        """
        Adds the provided parameters to the cURL command by replacing placeholders or empty 'params' arrays with actual values.
        Args:
            state (dict): The current graph state, containing the cURL command, input, and documents. The input contains the parameters needed for execution.

        Returns:
            str: The updated cURL command ready for execution.
        """
        
        command_output = state["generation"]
        input_question = state["input"]
        documents = state.get("documents", [])

        add_params_prompt = PromptTemplate(
            template="""
            <|begin_of_text|><|start_header_id|>system<|end_header_id|>
            Your task is to insert the provided parameters into the cURL command. The command has placeholders or an empty "params" array, 
            and your task is to replace those with the actual values provided within the input.

            RETURN THE PLAIN COMMAND, NO MARKDOWN  like this ```bash ```

            Follow these steps:
            1. Identify where the "params" array is located in the cURL command.
            2. Replace the placeholders or empty values with the actual parameter values provided within the input.
            3. Ensure that all provided parameters are correctly inserted into the command.

            Example:

            Input command:
            curl -X POST https://mainnet.infura.io/v3/{{infuraKey}} 
            -H "Content-Type: application/json" 
            -d '{{"jsonrpc":"2.0","method":"eth_getBlockByHash","params": ["<BLOCK_HASH>", true],"id":1}}'

            Parameters provided:
            {{"params": ["0x12345abcde...", true]}}

            Output:
            curl -X POST https://mainnet.infura.io/v3/{{infuraKey}} 
            -H "Content-Type: application/json" 
            -d '{{"jsonrpc":"2.0","method":"eth_getBlockByHash","params": ["0x12345abcde...", true],"id":1}}'
            
            Your output must return only the updated cURL command.

            <|eot_id|>
            <|start_header_id|>context<|end_header_id|>
            cURL Command: {generation}
            Input (which contains the params): {input}
            Documents for reference: {documents}

            <|eot_id|>
            <|start_header_id|>user<|end_header_id|>
            Insert the provided parameters into the cURL command and return the complete cURL command for execution.
            <|eot_id|>
            <|start_header_id|>assistant<|end_header_id|>
            """,
            input_variables=["generation", "input", "documents"]
        )
        
        add_params_interpreter = add_params_prompt | self.llm | StrOutputParser()
        updated_curl_command = add_params_interpreter.invoke({
            "generation": command_output, 
            "input": input_question,
            "documents": documents
        })
        
        return {
            "chat_history": state.get("chat_history", []),
            "input": state.get("input"),
            "documents": state.get("documents", []),
            "generation": updated_curl_command  
        }