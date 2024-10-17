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
            <|eot_id|>
            <|start_header_id|>assistant<|end_header_id|>
            """,
            input_variables=["document", "input"],  # No chat_history here
        )

        # Create the retriever chain
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

        
