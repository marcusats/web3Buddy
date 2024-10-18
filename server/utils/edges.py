import json

class EdgeGraph:
    def __init__(self, hallucination_grader, code_evaluator, create_action_evaluator, create_execution_evaluator, create_params_evaluator, paramsProvidedConfidence):
        self.hallucination_grader = hallucination_grader
        self.code_evaluator = code_evaluator
        self.create_action_evaluator = create_action_evaluator
        self.create_execution_evaluator = create_execution_evaluator
        self.create_params_evaluator = create_params_evaluator
        self.paramsProvidedConfidence = paramsProvidedConfidence


    def decide_to_generate(self, state):
        """
        Determines whether to generate an answer, or re-generate a question.

        Args:
            state (dict): The current graph state

        Returns:
            str: Binary decision for next node to call
        """
        print("---ASSESS GRADED DOCUMENTS---")
        question = state["input"]
        filtered_documents = state["documents"]
        if not filtered_documents:
            print("---DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, TRANSFORM QUERY---")
            return "transform_query"
        else:
            print("---DECISION: GENERATE---")
            return "generate"

    def grade_generation_v_documents_and_question(self, state):
        """
        Determines whether the generation is grounded in the document and answers question.

        Args:
            state (dict): The current graph state

        Returns:
            str: Decision for next node to call
        """
        print("---CHECK HALLUCINATIONS---")
        question = state["input"]
        documents = state["documents"]
        generation = state["generation"]
        score = self.hallucination_grader.invoke({"documents": documents, "generation": generation})
        grade = score["score"]
        if grade >= 0.5:
            print("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
            print("---GRADE GENERATION vs QUESTION---")
            score = self.code_evaluator.invoke({"input": question, "generation": generation, "documents": documents})
            grade = score["score"]
            if grade >= 0.5:
                print("---DECISION: GENERATION ADDRESSES QUESTION---")
                return "useful"
            else:
                print("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
                return "not useful"
        else:
            print("---DECISION: GENERATIONS ARE HALLUCINATED, RE-TRY---")
            return "not supported"

    def action_first(self, state):
        """
        Evaluates the user's question to decide the next action based on its content.

        Args:
            state (dict): The current graph state

        Returns:
            str: A string indicating the next action: "infura", "solidity", or "chat".
        """
        question = state["generation"]
        decision = self.create_action_evaluator.invoke({"question": question})
        if decision == "infura":
            print("---DECISION: INFURA---")
            state["vector_store_namespace"] = "infura-docs"
            return "infura"
        elif decision == "solidity":
            print("---DECISION: SOLIDITY---")
            state["vector_store_namespace"] = "solidity-docs"
            return "solidity"
        else:
            print("---DECISION: CHAT---")
            return "chat"

    def execution_action(self, state):
        """
        Determines if the user's question involves executing an Infura command and executes the action based on the decision.

        Args:
            state (dict): The current graph state

        Returns:
            str: The next node to call
        """
        print("---EXECUTE ACTION---")
        question = state["input"]
        decision = self.execution_evaluator.invoke({"question": question})
        if decision == "execute":
            print("---DECISION: EXECUTE INFURA COMMAND---")
            return "retrieveInfura"
        else:
            print("---DECISION: NO EXECUTION NEEDED---")
            return "chat"

    def decide_to_execute(self, state):
        """
        Evaluates the user's question to decide if it involves executing an Infura command.
        Uses a confidence score to assess how certain the system is about the decision to execute the command.

        Args:
            state (dict): The current graph state

        Returns:
            str: A string indicating the decision: "execute" or "no-execute".
        """
        print("---DECISION TO EXECUTE---")
        question = state["input"]
        generation = state["generation"]
        documents = state.get("documents", [])
        print(f"Determined documents: {documents}")
        decision_with_confidence = self.create_execution_evaluator.invoke({
            "question": question,
            "generation": generation,
            "documents": documents
        })
        print("--------DECISION---------")
        print(f"Decision with confidence (raw): {decision_with_confidence}")
        try:
            decision_data = json.loads(decision_with_confidence)
            confidence = decision_data.get("score", 0)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            confidence = 0
        print(f"Confidence score: {confidence}")
        confidence_threshold = 0.6
        if confidence >= confidence_threshold:
            print("---CONFIDENT: EXECUTE---")
            return "execute"
        else:
            print("---CONFIDENT: NO EXECUTE---")
            return "no-execute"

    def tool_direction(self, state):
        """
        Determines the next tool to use based on the user's question.

        Args:
            state (dict): The current graph state

        Returns:
            str: The next tool to use: "infura" or "solidity".
        """
        print("---TOOL DIRECTION---")
        vector = state["vector_store_namespace"]
        if vector == "infura-docs":
            print("---DECISION: INFURA---")
            return "infura"
        else:
            print("---DECISION: SOLIDITY---")
            return "solidity"
        
    
    def paramsCheck(self, state):
        """
        Checks if the user's command requires additional parameters for execution and decides the next action based on the evaluation.
        Incorporates a confidence score to assess how certain the system is about the decision.

        Args:
            state (dict): The current graph state

        Returns:
            str: The next node to call
        """
        print("---PARAMS CHECK---")
        question = state["input"]
        generation = state["generation"]
        documents = state.get("documents", [])
        print(f"Determined documents: {documents}")
        decision_with_confidence = self.create_params_evaluator.invoke({
            "question": question,
            "curl_command": generation,
            "documents": documents
        })
        print("--------DECISION---------")
        print(f"Decision with confidence (raw): {decision_with_confidence}")
        try:
            decision_data = json.loads(decision_with_confidence)
            confidence = decision_data.get("score", 0)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            confidence = 0
        print(f"Confidence score: {confidence}")
        confidence_threshold = 0.6
        if confidence >= confidence_threshold:
            print("---CONFIDENT: PARAMS ARE NEEDED---")
            return "params-needed"
        else:
            print("---CONFIDENT: NO PARAMS ARE NEEDED---")
            return "no-params-needed"

    def paramsProvided(self, state):
        """
        Checks if the user likely provided the necessary parameters for execution based on the evaluation of the input.
        Uses a confidence score to assess how certain the system is about the presence of parameters.

        Args:
            state (dict): The current graph state

        Returns:
            str: The next node to call ("params-provided" or "params-not-provided")
        """
        print("---PARAMS PROVIDED---")
        question = state["input"]
        generation = state["generation"]
        documents = state.get("documents", [])
        decision_with_confidence = self.paramsProvidedConfidence.invoke({
            "input": question,
        })
        print("--------DECISION---------")
        print(f"Decision with confidence (raw): {decision_with_confidence}")
        try:
            decision_data = json.loads(decision_with_confidence)
            confidence_score = decision_data.get("score", 0.0)
            print(f"Decision with confidence score: {confidence_score}")
            confidence_threshold = 0.6
            if confidence_score >= confidence_threshold:
                print("---DECISION: PARAMS PROVIDED---")
                return "params-provided"
            else:
                print("---DECISION: PARAMS NOT PROVIDED---")
                return "params-not-provided"
        except json.JSONDecodeError as e:
            print(f"Error parsing decision: {e}")
            print("Falling back to 'params-not-provided' due to parsing issue.")
            return "params-not-provided"