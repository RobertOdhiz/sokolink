'''
Build a Sokolink compliance workflow that connects four agents to provide business compliance guidance.
'''

from pydantic import BaseModel, Field
import uuid
from ibm_watsonx_orchestrate.flow_builder.flows import END, Flow, flow, START
from typing import List, Dict, Any, Optional

# Input schema for the workflow
class WorkflowInput(BaseModel):
    user_message: str
    session_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))


# Output schema for the workflow
class WorkflowOutput(BaseModel):
    session_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    compliance_steps: List[Dict[str, Any]]
    total_estimated_cost: float
    total_timeline_days: int
    business_type: str
    location: str

# Schema for classifier output
class ClassifierOutput(BaseModel):
    business_type: str
    location: str
    specific_area: Optional[str] = None
    products: List[str] = []
    confidence_score: float

# Schema for regulatory mapper output
class RegulatoryMapperOutput(BaseModel):
    requirements: List[Dict[str, Any]]

# Schema for data synthesizer output  
class DataSynthesizerOutput(BaseModel):
    detailed_steps: List[Dict[str, Any]]

@flow(
    name="sokolink_compliance_workflow",
    input_schema=WorkflowInput,
    output_schema=WorkflowOutput
)
def build_sokolink_workflow(aflow: Flow = None) -> Flow:
    """
    Complete workflow for providing business compliance guidance to small entrepreneurs in Kenya.
    Takes user message about their business and returns a structured compliance roadmap.
    """
    
    # Step 1: Classify business type and location
    classifier_node = aflow.agent(
        name="business_classifier",
        agent="intent_classifier",
        message="Analyze this business query and extract business type and location: {{flow.input.user_message}}",
        description="Classifies business type and location from user message",
        input_schema=WorkflowInput,
        output_schema=ClassifierOutput
    )
    
    # Step 2: Map to regulatory requirements
    regulatory_mapper_node = aflow.agent(
        name="regulatory_mapper",
        agent="regulatory_mapper_agent", 
        message="""
        Based on the business classification, identify all required permits and licenses.
        Business Type: {{business_classifier.output.business_type}}
        Location: {{business_classifier.output.location}}
        """,
        description="Maps business type to relevant regulatory requirements",
        input_schema=ClassifierOutput,
        output_schema=RegulatoryMapperOutput
    )
    
    # Step 3: Synthesize into actionable steps
    data_synthesizer_node = aflow.agent(
        name="data_synthesizer",
        agent="data_synthesizer",
        display_name="Data Synthesizer", 
        message="""
        Convert these regulatory requirements into detailed, actionable steps with costs and timelines:
        {{regulatory_mapper.output.requirements}}
        """,
        description="Creates actionable compliance steps from regulations",
        input_schema=RegulatoryMapperOutput,
        output_schema=DataSynthesizerOutput
    )
    
    # Step 4: Generate final structured output
    planner_node = aflow.agent(
        name="personalized_planner",
        agent="personalized_planner_agent",
        display_name="Personalized Planner",
        message="""
        Compile all information into the final structured format.
        Detailed Steps: {{data_synthesizer.output.detailed_steps}}
        Session ID: {{flow.input.session_id}}
        Business Type: {{business_classifier.output.business_type}}
        Location: {{business_classifier.output.location}}
        
        Return the exact JSON format expected by the FastAPI backend.
        """,
        description="Generates final structured compliance roadmap",
        input_schema=DataSynthesizerOutput,
        output_schema=WorkflowOutput
    )
    
    # Connect all nodes in sequence using the same pattern as hello world example
    aflow.edge(START, classifier_node)
    aflow.edge(classifier_node, regulatory_mapper_node)
    aflow.edge(regulatory_mapper_node, data_synthesizer_node)
    aflow.edge(data_synthesizer_node, planner_node)
    aflow.edge(planner_node, END)

    return aflow