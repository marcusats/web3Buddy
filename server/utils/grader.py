from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain import hub

class GraderUtils:
    def __init__(self, model):
        self.model = model

    def create_retrieval_grader(self):
        """
        Creates a retrieval grader that assesses the relevance of a retrieved document to a user question.

        Returns:
            A callable function that takes a document and a question as input and returns a JSON object with a binary score indicating whether the document is relevant to the question.
        """
        grade_prompt = PromptTemplate(
            template="""
            <|begin_of_text|><|start_header_id|>system<|end_header_id|>
            You are a grader assessing relevance of a retrieved document to a user question. If the document contains keywords related to the user question, grade it as relevant. It does not need to be a stringent test. The goal is to filter out erroneous retrievals.
            Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question.
            Provide the binary score as a JSON with a single key 'score' and no preamble or explanation.
            <|eot_id|>
            <|start_header_id|>user<|end_header_id|>

            Here is the retrieved document: \n\n {document} \n\n
            Here is the user question: {input} \n
            Here is a rewrited question that might be more clear: {rewrited_question}
            <|eot_id|>
            <|start_header_id|>assistant<|end_header_id|>
            """,
            input_variables=["document", "input", "rewrited_question"],
        )

        retriever_grader = grade_prompt | self.model | JsonOutputParser()

        return retriever_grader

    def create_hallucination_grader(self):
        """
        Creates a hallucination grader that assesses whether an answer is grounded in/supported by a set of facts using a confidence score.

        Returns:
            A callable function that takes a generation (answer) and a list of documents (facts) as input and returns a score (0-1) indicating how grounded the answer is in the facts.
        """
        hallucination_prompt = PromptTemplate(
            template="""
            <|begin_of_text|><|start_header_id|>system<|end_header_id|>
            You are a grader assessing whether an answer is grounded in/supported by a set of facts.
            
            Provide a confidence score between 0 and 1 indicating how well the answer is grounded in the facts. 
            
            The score should be higher if the answer uses the facts correctly and logically, and lower if there are inconsistencies or the facts don't fully support the answer.

            Provide the score as a JSON with a single key 'score' and no preamble or explanation.

            <|eot_id|>
            <|start_header_id|>user<|end_header_id|>
            Here are the facts:
            \n ------- \n
            {documents}
            \n ------- \n
            Here is the answer: {generation}
            <|eot_id|>
            <|start_header_id|>assistant<|end_header_id|>
            """,
            input_variables=["generation", "documents"],
        )

        hallucination_grader = hallucination_prompt | self.model | JsonOutputParser()

        return hallucination_grader

    def create_code_evaluator(self):
        """
        Creates a code evaluator that assesses whether the generated code is correct and relevant to the given question.

        Returns:
            A callable function that takes a generation (code), a question, and a list of documents as input and returns a JSON object with a score (0-1) and feedback.
        """
        eval_template = PromptTemplate(
            template="""<|begin_of_text|><|start_header_id|>system<|end_header_id|> You are a code evaluator assessing whether the generated code is correct and relevant to the given question.
            Provide a JSON response with the following keys:

            'score': A score between 0 and 1 indicating how correct and relevant the code is.
            'feedback': A brief explanation of your evaluation, including any issues or improvements needed.

            <|eot_id|><|start_header_id|>user<|end_header_id|>
            Here is the generated code:
            \n ------- \n
            {generation}
            \n ------- \n
            Here is the question: {input}
            \n ------- \n
            Here are the relevant documents: {documents}
            <|eot_id|><|start_header_id|>assistant<|end_header_id|>""",
            input_variables=["generation", "input", "documents"],
        )

        code_evaluator = eval_template | self.model | JsonOutputParser()

        return code_evaluator

    def create_question_rewriter(self):
        """
        Creates a question rewriter chain that rewrites a given question to improve its clarity and relevance.

        Returns:
            A callable function that takes a question as input and returns the rewritten question as a string.
        """
        re_write_prompt = hub.pull("efriis/self-rag-question-rewriter")
        question_rewriter = re_write_prompt | self.model | StrOutputParser()

        return question_rewriter
    
    def create_action_evaluator(self):
        """
        Evaluates the user's question to decide the next action based on its content.

        Returns:
            A string indicating the next action: "infura", "solidity", or "chat".
        """
        decision_prompt = PromptTemplate(
            template="""
            <|begin_of_text|><|start_header_id|>system<|end_header_id|>
            You are a decision maker responsible for determining the appropriate action based on the user's question. You have access to three primary tools:

            1. **Infura**: This tool interacts with the blockchain to retrieve real-time data, such as querying for information on transactions, blocks, gas prices, and account balances, etc. Choose "infura" if the user’s question requires information directly from the blockchain or requests any API calls to the blockchain using Infura or anything realted to the infura service.

            2. **Solidity**: This tool handles questions related to smart contracts, their syntax, improvements, deployment, or code optimizations. Choose "solidity" if the question is about writing, understanding, or optimizing smart contract code.

            3. **Chat**: Choose "chat" if the question is general, conversational, or doesn’t directly involve blockchain data or smart contract development.

            Based on the content of the question, determine the best tool to use and respond with a single word: "infura", "solidity", or "chat".

            <|eot_id|>
            <|start_header_id|>user<|end_header_id|>
            Here is the question: {question}
            <|eot_id|>
            <|start_header_id|>assistant<|end_header_id|>
            """,
            input_variables=["question"],
        )

        action_decision = decision_prompt | self.model | StrOutputParser()

        return action_decision
    
    def create_execution_evaluator(self):
        """
        Evaluates the user's question to decide how confident the system is that a blockchain command (via curl) needs to be executed.
        It checks for real-time data queries, previous generations for context, and evaluates whether the execution is appropriate.

        Returns:
            A confidence score (from 0 to 1) indicating how likely it is that the command should be executed.
        """
        execution_prompt = PromptTemplate(
            template="""
            <|begin_of_text|><|start_header_id|>system<|end_header_id|>
            Your task is to evaluate how confident you are that the user's question requires executing a curl command to fetch real-time blockchain information.

            Follow this step-by-step process:
            1. Review previous generations for any mention of a curl command. If a curl command was previously generated and the context 
            matches the current question, increase the confidence score.
            2. If the question involves fetching real-time data from the blockchain, such as block number, gas price, or transaction status, 
            and the question could be answered by querying the blockchain, increase the confidence score. 
            3. Review the provided documents to check if any real-time blockchain queries or curl commands are relevant to the user's current question.
            4. The confidence score should range between 0 and 1. The higher the score, the more likely it is that the execution is required.

            Provide a JSON response with the following key:

            - 'score': A confidence score between 0 and 1 indicating how likely it is that executing the curl command is necessary.

            DO NOT ADD MARKDOWN NOTATION, PLAIN OBJECT ```json

            Example:

            Previous Generation: {generation}
            Question: {question}

            - If the question involves fetching real-time data such as a block hash or gas price, and a previously generated curl command exists, the confidence score should be closer to 1 (e.g., 0.9).
            - If the query is more theoretical and does not require real-time data, the confidence score should be lower (e.g., 0.2).

            <|eot_id|>
            <|start_header_id|>context<|end_header_id|>
            Previous Generation: {generation}
            Documents: {documents}

            <|eot_id|>
            <|start_header_id|>user<|end_header_id|>
            Here is the question: {question}
            <|eot_id|>
            <|start_header_id|>assistant<|end_header_id|>
            """,
            input_variables=["question", "generation", "documents"],
        )

        execution_confidence = execution_prompt | self.model | StrOutputParser()

        return execution_confidence
    
    def create_params_evaluator(self):
        """
        Evaluates the user's question to decide if it involves executing a blockchain command (specifically via curl).
        It checks for real-time data queries, previous generations for context, and ensures that if the question 
        requires real-time data and a curl command is appropriate, it decides to execute.

        Returns:
            A string indicating the decision: "execute" or "no-execute".
        """
        execution_prompt = PromptTemplate(
            template="""
            <|begin_of_text|><|start_header_id|>system<|end_header_id|>
            You are responsible for deciding if the user's question requires executing a curl command to fetch real-time blockchain information.

            Here is your decision-making process:
            1.Review previous generations for any mention of a curl command. If a curl command was previously generated and the context 
            matches the current question, decide to execute.
            2. . If the question involves fetching real-time data from the blockchain, such as block number, gas price, or transaction status, 
            and the question could be answered by querying the blockchain, decide to execute. 
            3. Review the provided documents to check if any real-time blockchain queries or curl commands are relevant to the user's current question.

            Your decision must be one of the following:
            - "execute": If a curl command is relevant to the query (either previously mentioned or inferred).
            - "no-execute": If the query does not involve real-time blockchain data or no curl command is needed.

            Provide your decision as a single string without any additional explanation.

            <|eot_id|>
            <|start_header_id|>context<|end_header_id|>
            Previous Generation: {generation}
            Documents: {documents}

            <|eot_id|>
            <|start_header_id|>user<|end_header_id|>
            Here is the question: {question}
            <|eot_id|>
            <|start_header_id|>assistant<|end_header_id|>
            """,
            input_variables=["question", "generation", "documents"],
        )

        execution_decision = execution_prompt | self.model | StrOutputParser()

        return execution_decision
    
    def create_params_evaluator(self):
        """
        Evaluates the cURL command to decide how confident the system is that specific parameters (like address, block number)
        are required for execution, based on the method call, relevant documentation, and the presence of a non-empty "params" array in the cURL command.

        The function analyzes the command, looks for method calls, checks the provided documentation, and evaluates if the user's 
        question or command likely needs specific parameters for execution.

        Returns:
            A confidence score (from 0 to 1) that indicates how sure the system is that parameters are required.
        """

        params_prompt = PromptTemplate(
            template="""
            <|begin_of_text|><|start_header_id|>system<|end_header_id|>
            Your task is to evaluate whether the user's cURL command likely requires additional parameters for execution, 
            based on the method being called, the presence of parameters in the "params" array, and the provided documentation.
            Provide a JSON response with the following keys and nothing else, no feedback no nothing, just the JSON object:
            'score': confidence score between 0 and 1 indicating how likely it is that parameters are required for execution.

            DO NOT ADD MARKDOWN NOTATION, PLAIN OBJECT ```json
        
            
            Follow this step-by-step process:
            1. Extract the **method** field from the cURL command (e.g., "eth_chainId", "eth_getBalance"). The method field is always inside the `"method":` key in the command's data payload signaled after the `-d` flag.
            2. If the "params" array in the cURL command is **not empty**, increase the confidence score as this indicates parameters are likely needed.
            3. Reference the provided documentation to determine whether the identified method requires parameters like `address`, `block`, or other values for successful execution.
            4. Ignore any API keys, as those will be handled separately.
            5. Based on the "params" array and the method requirements in the documentation, provide a confidence score (from 0 to 1) for how likely it is that parameters are needed for the method.

            Example:

            curl https://mainnet.infura.io/v3/YOUR-API-KEY 
            -X POST 
            -H "Content-Type: application/json" 
            -d '{{"jsonrpc":"2.0","method":"eth_chainId","params": [],"id":1}}'
            
            - In this case, the method `"eth_chainId"` is called.
            - The "params" array is empty.
            - According to the documentation, `"eth_chainId"` does not require any parameters, so the confidence score should be 0.1 (indicating low likelihood that parameters are needed).

            Another Example:

            curl https://mainnet.infura.io/v3/YOUR-API-KEY 
            -X POST 
            -H "Content-Type: application/json" 
            -d '{{"jsonrpc":"2.0","method":"eth_getBlockByHash","params": ["0x12345...", false],"id":1}}'
            
            - In this case, the method `"eth_getBlockByHash"` is called.
            - The "params" array is **not empty**, which indicates that parameters are likely required.
            - The documentation confirms that this method requires `hash` and `transaction details flag` parameters, so the confidence score should be 1.0 (indicating high likelihood that parameters are needed).

            <|eot_id|>
            <|start_header_id|>context<|end_header_id|>
            cURL Command: {curl_command}
            User Question: {question}
            Documents for reference:
            {documents}

            <|eot_id|>
            <|start_header_id|>user<|end_header_id|>
            The user has provided this cURL command. Identify how likely it is that parameters are required for execution and provide a confidence score (0 to 1).
            <|eot_id|>
            <|start_header_id|>assistant<|end_header_id|>
            """,
            input_variables=["question", "curl_command", "documents"],
        )

        params_confidence = params_prompt | self.model | StrOutputParser()

        return params_confidence

    def paramsProvidedConfidence(self):
        """
        Evaluates the user's question and checks if parameters were passed in the input, returning a confidence score.
        The score ranges from 0 to 1 based on how likely it is that the input contains parameters either through an explicit 'params' key or
        mentioned within the input text.

        Returns:
            A JSON object with a 'score' indicating confidence from 0 to 1.
        """

        params_prompt = PromptTemplate(
            template="""
                    <|begin_of_text|><|start_header_id|>system<|end_header_id|>
                    You are responsible for evaluating the user's input to determine how likely it is that parameters are provided.
                    Provide a JSON response with the following key and nothing else, no feedback, no explanation, just the JSON object:
                    score: confidence score between 0 and 1 indicating how likely it is that parameters are provided in the input.

                    DO NOT ADD MARKDOWN NOTATION, PLAIN OBJECT ```json

                    Follow this step-by-step process:
                    1. Check if the params key exists in the input. If it does and contains a non-empty list of parameters, the confidence score should be close to 1.0.
                    2. If the params key is missing, analyze the input text to check if parameters (e.g., block number, hash, etc.) are explicitly mentioned.
                    3. Increase the confidence score based on how clear the parameter mentions are.
                    4. If no parameters are found, the confidence score should be close to 0.0.

                    Example 1:
                    Question: Execute eth_getBlockByHash with block hash and details.
                    Input: {{params: [0x12345..., true]}}
                    

                    Example 2:
                    Question: Execute eth_getBlockByHash for block 0x12345 with details flag set to true.
                    Input: Execute eth_getBlockByHash for block 0x12345 with details flag set to true.
                    R 
                    Example 3:
                    Question: Execute eth_chainId.
                    Input: {{params: []}}
            

                    Example 4:
                    Question: What is the current chain ID?
                    Input: What is the current chain ID?
                   

                    Provide your final output as a JSON object:
                        score: 0.0 to 1.0
                    

                    <|eot_id|>
                    <|start_header_id|>context<|end_header_id|>
                    User Input: {input}

                    <|eot_id|>
                    <|start_header_id|>user<|end_header_id|>
                    The user has provided this input. Determine the likelihood that parameters are provided, and provide a confidence score (0 to 1).
                    <|eot_id|>
                    <|start_header_id|>assistant<|end_header_id|>
            """,
            input_variables=["input"]
        )

        params_confidence = params_prompt | self.model | StrOutputParser()

        return params_confidence