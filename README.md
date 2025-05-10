# OWLBEAR
![OWLBEAR logo](images/owlbear_logo.png)
OWLBEAR: Orchestrated Workflow Logic with Bespoke Experts for Agentic Routines

## Overview
OWLBEAR is a framework designed to simplify the creation and management of agentic AI workflows. By combining Orchestrated Workflow Logic with Bespoke Experts , OWLBEAR empowers developers and enterprises to build reliable, scalable, and customizable AI-driven solutions.

Whether you're automating business processes, solving complex problems, or fostering innovation, OWLBEAR provides the tools and structure needed to streamline your workflows and achieve your goals.


## Key Features
- Modular Expert System : Leverage a library of pre-defined experts (e.g., Executive Coach, Strategic Thinking Partner,Communication Strategist) or create your own bespoke experts tailored to your needs.
- Customizable Endpoints : Connect to various LLMs and APIs by configuring endpoints for each expert.
- Orchestrated Workflows : Seamlessly integrate multiple experts into cohesive workflows that align with your business objectives.
- Workflow Validation : Validate workflows before execution to catch errors, expand variables, and provide human-readable documentation.
- Equip Agents with Tools : Allow your experts to be more autonomous and affect their environment using tools. 
- Agentic Routines : Enable AI agents to execute tasks autonomously, reason through challenges, and adapt to dynamic environments by combining orchestrated workflows with tool-using experts.

## Installation
To get started with OWLBEAR, follow these steps:

1. Clone the repository:
```bash
git clone https://github.com/jvroig/OWLBEAR.git
cd OWLBEAR
```

2. Create virtual environment and install requirements:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Copy `endpoint_config_sample.yaml` to `endpoint_config.yaml`
```bash
cp endpoint_config_sample.yaml endpoint_config.yaml
```

4. Open `endpoint_config.yaml` in your editor and update with your actual endpoint information.
The sample file shows a list of different endpoints. Currently, OWLBEAR will only use the first endpoint you put in the list. You can remove the superfluous entries. 
In the future, fallback will be implemented to use the additional endpoints.

5. Create a `.env` file in the project's root directory to place your API KEY. See "Experts" section for matching API Key values in .env with endpoint config. 

## Usage

### Running Workflows
To run one of the sample workflows:
```bash
python3 owlbear.py workflows/sequences/helloworld.yml
```

### Workflow Validation
Before running complex workflows, you can validate them to catch potential errors:

```bash
# Validate only (without executing the workflow)
python3 owlbear.py workflows/sequences/variables_demo.yml --strings workflows/strings/variables_example.yaml --validate-only

# Validate as part of normal execution (happens by default)
python3 owlbear.py workflows/sequences/variables_demo.yml --strings workflows/strings/variables_example.yaml

# Skip validation and execute directly
python3 owlbear.py workflows/sequences/variables_demo.yml --strings workflows/strings/variables_example.yaml --skip-validation
```

You can also use the standalone validator tool directly:

```bash
python3 workflow_validator.py workflows/sequences/variables_demo.yml --strings workflows/strings/variables_example.yaml
```

The validator generates a human-readable expanded workflow file (`validator.yaml`) with all string references and variables resolved, making it easier to audit and understand the workflow before execution.

You can also provide user input via the command line:
```bash
python3 owlbear.py workflows/flow_with_user_input.yml --user-input "What is the capital of France?"
```

### Using External String Variables
You can decouple string variables from workflow definitions by storing them in a separate YAML file:
```bash
python3 owlbear.py workflows/sequences/flow_external_strings.yml --strings workflows/strings/strings_sample.yaml
```

This separation allows you to:
- Reuse the same string variables across multiple workflows
- Change string variables without modifying workflow definitions
- Maintain cleaner workflow files that focus only on action sequences

### Using Template Variables in Strings
OWLBEAR supports template variables within string definitions using double curly braces syntax `{{variable_name}}`. This makes string management even more flexible:

```yaml
# Example strings file with variables
VARIABLES:
  name: "John Doe"
  company: "Acme Corporation"
  tool: "OWLBEAR"

STR_greeting: "Hello {{name}}, welcome to {{company}}!"
STR_tool_info: "{{tool}} is a workflow orchestration engine."
```

Variables can be used in any string definition and will be automatically substituted when the workflow runs. You can use variables in both external string files and embedded STRINGS sections. Variables offer many benefits:

- Create reusable template phrases with customizable placeholders
- Centralize configuration values that appear in multiple strings
- Easily update values across an entire workflow by changing a single variable
- Make workflows more maintainable and less error-prone

Variables can be used in any string where the variable appears inside double curly braces, including in the inputs to PROMPT and DECIDE actions. The variables will be substituted in all of these contexts:

1. In string definitions in the STRINGS section or external strings file
2. In literal strings within workflow actions (like PROMPT inputs)
3. In any string returned by previous actions

Example of inline variable usage in a workflow action:
```yaml
ACTIONS:
  - PROMPT:
      expert: "HelpfulAssistant"
      inputs:
        - STR_greeting
        - "Please tell {{name}} about the {{project}} at {{company}}."
      output: step1
```

In this simple example from databreach.yml, 3 experts work together to create a data breach response plan:
- CEO
- Strategic Thinking Partner
- Ethical Decision Making Counselor

After a workflow runs, you can view the outputs in the `outputs/[workflow_name]_[timestamp]/` folder

## Experts
You can define your own AI Experts in the `experts` folder.

Use the pre-built sample experts as a template.

The `ApiKey` property defines which entry in your `.env` file should be used. For example:
```yaml
ExpertID: MyExpert
Description: Testing
SystemPrompt: Awesome prompt here
Endpoint:
  Host: "127.0.0.1"
  Port: "8000"
  Model: "Qwen/Qwen2.5-72B-Instruct"
ApiKey: MY_SECRET_API_KEY
```

The above will work if MY_SECRET_API_KEY exists in the `.env` file at the root of the project:
```
MY_SECRET_API_KEY=abcdef42069
```

`ApiKey` can be the API Key for any LLM API endpoint - OpenAI, Anthropic, Alibaba Cloud Model Studio, etc. You can store an unlimited number of API keys in `.env`.

In workflows, experts are identified using their `ExpertID` value.

## Tools
Experts can be given tools by populating `ToolsAvailable` with a list if tools defined in the server. Example: (`experts/cto.yaml`)
```yaml
ExpertID: CTO
Description: Agentic AI that employs CTO-like thinking to guide technology strategy, innovation, and execution.
SystemPrompt: You are a CTO, embodying the strategic thinking, technical expertise, and leadership skills of a top technology executive. Your role is to provide high-level guidance on technology strategy, innovation, and execution. You excel at aligning technology initiatives with business goals, driving digital transformation, and ensuring scalability and security. Offer clear, actionable advice on topics such as software architecture, team leadership, emerging technologies, and risk management, always with a focus on delivering value to the organization.
ToolsAvailable:
  - write_file
  - read_file
  - create_directory
  - list_directory
```
These tools have to exist in the server.

In the current prototype tool-calling, these tools are defined in `inference/tools_lib`

## Workflows
Workflows are a series of ACTIONS.

ACTIONS are building blocks composed of EXPERTS, input, and output.

OWLBEAR supports three types of actions:
- **PROMPT**: Send a prompt to an expert and get a response
- **DECIDE**: Make a decision that can control workflow flow (TRUE continues, FALSE loops back)
- **COMPLEX**: Use predefined action templates that expand into sequences of basic actions

### Example 1: Hello World
Here's a "Hello World" example (`helloworld.yml`):
```YAML
ACTIONS:
  - PROMPT:
      expert: CEO
      inputs:
        - Please say "Hello, World!"
      output: hello_world.yml
```

Run that with:

```bash
python3 owlbear.py workflows/sequences/helloworld.yml
```

After that executes, inside `outputs/helloworld_[timestamp]/` you will find a `hello_world.yml` file containing something like this:
```yaml
action_type: PROMPT
content: Hello, World! Welcome to our discussions on strategic leadership and organizational growth. How can I assist you today in achieving your business objectives?
expert: CEO
inputs:
- Please say "Hello, World!"
timestamp: 1743857370.9444122
```

Changing the expert will change the output since they have different personalities c/o the system prompt.

### Example 2: Test with named strings 
This is a slightly more complicated example, using named strings and multiple inputs (`test.yml`)
```yaml
STRINGS:
  STR_intro_prompt: "We are a financial institution, and we just suffered a major data breach that exposed private data for some of our customers. We need to decide how we respond to this in order to appease customers and regulatory agencies and come up with a response plan."
  STR_delimiter: "*********************************************"

ACTIONS:
  - PROMPT:
      expert: "Strategic Thinking Partner"
      inputs:
        - STR_intro_prompt
        - STR_delimiter
        - Create a strategy that can help us deal with this event. It should be specific, actionable, and readily executable. Use markdown formatting.
      output: test01
```

Run that with:

```bash
python3 owlbear.py workflows/sequences/test.yml
```

After that executes, inside `outputs/test_[timestamp]/` you will find a `test01.yml` file containing something like this:
```yaml
action_type: PROMPT
content: |-
  # Data Breach Response Strategy

  ## Objective
  To manage the aftermath of the data breach effectively, ensuring customer trust is maintained and regulatory compliance is achieved.

  ## Immediate Actions

  ### 1. Containment and Investigation
  - **Action**: Immediately isolate affected systems to prevent further data loss or unauthorized access.
  - **Assign**: IT Security Team
  - **Timeline**: Within 24 hours

  ### 2. Notification
  - **Action**: Notify all affected customers and relevant regulatory bodies as per legal requirements.
  - **Assign**: Legal and Compliance Department
  - **Timeline**: Within 72 hours

  ### 3. Public Communication
  - **Action**: Issue a public statement acknowledging the breach, explaining what happened, and outlining the steps being taken.
  - **Assign**: Public Relations Department
  - **Timeline**: Within 72 hours

  ## Long-Term Actions

  ### 4. Customer Support
  - **Action**: Set up a dedicated support line and email address for customers to inquire about the breach and receive updates.
  - **Assign**: Customer Service Team
  - **Timeline**: Ongoing

  ### 5. Credit Monitoring Services
  - **Action**: Offer free credit monitoring services to affected customers for a period of at least one year.
  - **Assign**: Risk Management Department
  - **Timeline**: Within 7 days

  ### 6. Internal Review and Policy Update
  - **Action**: Conduct an internal review to identify weaknesses in current security measures and update policies accordingly.
  - **Assign**: IT Security Team & Compliance Department
  - **Timeline**: Within 30 days

  ### 7. Training and Awareness
  - **Action**: Provide mandatory training sessions for employees on data security best practices.
  - **Assign**: Human Resources Department & IT Security Team
  - **Timeline**: Within 60 days

  ### 8. External Audit
  - **Action**: Engage an external auditor to review our security protocols and provide recommendations.
  - **Assign**: Audit Committee
  - **Timeline**: Within 90 days

  ## Monitoring and Evaluation

  ### 9. Continuous Monitoring
  - **Action**: Implement continuous monitoring of system vulnerabilities and suspicious activities.
  - **Assign**: IT Security Team
  - **Timeline**: Ongoing

  ### 10. Regular Reporting
  - **Action**: Prepare regular reports on the status of the recovery process and any new developments.
  - **Assign**: IT Security Team & Compliance Department
  - **Timeline**: Monthly

  ## Communication Plan

  ### 11. Stakeholder Updates
  - **Action**: Schedule regular updates to key stakeholders including board members, shareholders, and regulatory agencies.
  - **Assign**: Communications Department
  - **Timeline**: Bi-weekly for the first month, then monthly

  ### 12. Customer Engagement
  - **Action**: Organize webinars or Q&A sessions to keep customers informed and address concerns directly.
  - **Assign**: Customer Service Team & Communications Department
  - **Timeline**: Monthly for the first six months

  ## Conclusion
  This strategy aims to mitigate the immediate and long-term impacts of the data breach while reinforcing trust and compliance. Each action should be closely monitored and adjusted based on feedback and evolving circumstances.
expert: Strategic Thinking Partner
inputs:
- We are a financial institution, and we just suffered a major data breach that exposed private data for some of our customers. We need to decide how we respond to this in order to appease customers and regulatory agencies and come up with a response plan.
- '*********************************************'
- Create a strategy that can help us deal with this event. It should be specific, actionable, and readily executable. Use markdown formatting.
timestamp: 1743858034.689798
```

### Example 3: Data Breach Response Plan Collaboration
In this simple example, 3 experts work together to create a data breach response plan:
- CEO
- Strategic Thinking Partner
- Ethical Decision Making Counselor

File: `workflows/sequences/databreach.yml`
```yaml
STRINGS:
  STR_intro_prompt: "We are a financial institution, and we just suffered a major data breach that exposed private data for some of our customers. We need to decide how we respond to this in order to appease customers and regulatory agencies and come up with a response plan."
  STR_delimiter: "*********************************************"

ACTIONS:
  - PROMPT:
      expert: "Strategic Thinking Partner"
      inputs:
        - STR_intro_prompt
      output: strat_response_01
  
  - PROMPT:
      expert: "Ethical Decision Making Counselor"
      inputs:
        - STR_intro_prompt
      output: ethical_response_01  

  - PROMPT:
      expert: "CEO"
      inputs:
        - STR_intro_prompt.
        - Two experts were asked for their ideas.
        - "This was the first response: "
        - strat_response_01
        - "This was the second response: "
        - ethical_response_01
        - Synthesize and improve these responses to come up.
      output: ceo_synthesis_01

  - DECIDE:
      expert: "CEO"
      inputs:
        - STR_intro_prompt.
        - "This is the current response plan: "
        - ceo_synthesis_01
        - If you think this is good enough as the final response plan, say TRUE.
      output: ceo_greenlight
      loopback: 1
      loop_limit: 10

  - PROMPT:
      expert: "CEO"
      inputs:
        - STR_intro_prompt.
        - Below is the is the final approved response plan.
        - STR_delimiter
        - ceo_synthesis_01
        - Turn that into markdown as our final response. Output nothing else but the markdown contents.
      output: final_answer
```

In this workflow:
- Two different experts are independently asked to respond to the incident.
- Both of their outputs are then synthesized by the CEO expert.
- That synthesis is then reviewed by the CEO, to see if the plan seems good enough already.
    - If FALSE, the process will loop back to step 1.
    - If TRUE, the workflow continues
- The CEO expert will create a markdown version of the final plan.

All of the intermediate and final outputs can be seen in the `outputs/databreach_[timestamp]/` folder

### Example 4: Complex Actions
Complex Actions are predefined templates that expand into sequences of basic actions (PROMPT and DECIDE). They make workflow declarations more modular, reusable, and easier to understand.

File: `workflows/sequences/test_complex.yml`
```yaml
STRINGS:
  STR_intro_prompt: "We are a financial institution, and we just suffered a major data breach that exposed private data for some of our customers."

ACTIONS:
  - PROMPT:
      expert: "Strategic Thinking Partner"
      inputs:
        - STR_intro_prompt
      output: strat_response_01
  
  - COMPLEX:
      action: polished_output
      expert: CEO
      data:
        instruction: "Create a comprehensive response plan to the data breach."
        another_data: "Consider legal, ethical, and public relations implications."
        and_another: "The plan should be actionable and clear."
      output: polished_response_plan
  
  - PROMPT:
      expert: "Ethical Decision Making Counselor"
      inputs:
        - "Please review this response plan:"
        - polished_response_plan
      output: ethical_review
```

In this workflow:
1. A Strategic Thinking Partner provides initial input
2. The `polished_output` complex action is used to create a polished response plan
3. An Ethical Decision Making Counselor reviews the final plan

#### How Complex Actions Work

Complex Actions are defined in YAML files in the `actions/complex` directory. Each file contains a sequence of basic actions (PROMPT and DECIDE) with variable placeholders.

Example Complex Action definition (`actions/complex/polished_output.yml`):
```yaml
ACTIONS:
- PROMPT:
    id: polished_output_beginning
    expert: {{expert}}
    inputs:
      - "Let's create a polished output together."
      - "Instructions: {{instruction}}"
      - "First, create an initial draft."
    output: initial_draft

- PROMPT:
    expert: {{expert}}
    inputs:
      - "Let's review the initial draft:"
      - initial_draft
      - "{{another_data}}"
      - "Suggest improvements."
    output: suggested_improvements

- PROMPT:
    expert: {{expert}}
    inputs:
      - "Create a final revised version."
      - "Initial draft:"
      - initial_draft
      - "Suggested improvements:"
      - suggested_improvements
      - "Additional context: {{and_another}}"
    output: final_version

- DECIDE:
    expert: {{expert}}
    inputs:
      - "Evaluate the quality of this final output:"
      - final_version
      - "Is this of high quality? TRUE/FALSE"
    output: quality_evaluation
    loopback_target: polished_output_beginning
    loop_limit: 3
```

When a workflow is loaded, OWLBEAR expands all Complex Actions into their basic components, substituting the variables with the values provided in the `data` section.

#### Benefits of Complex Actions
- **Reusability**: Define common action patterns once and reuse them across workflows
- **Abstraction**: Hide complex implementation details behind a simple interface
- **Consistency**: Ensure similar tasks are handled in a consistent way
- **Maintainability**: Update a Complex Action template to improve all workflows that use it

You can create your own Complex Actions for any repeatable workflow patterns, such as:
- Polished content creation
- Comparative analysis
- Research and review processes
- Iterative refinement loops

### Example 5: Tool Use
In this simple example, we have only one expert, but it will use tools to create a report file directly instead of just having it in its text response.

File: `workflows/sequences/report_creation.yml`
```yaml
STRINGS:
  STR_intro_prompt: "We are a financial institution, and we just suffered a major data breach that exposed private data for some of our customers. We need to decide how we respond to this in order to appease customers and regulatory agencies and come up with a response plan."
  STR_delimiter: "*********************************************"
  STR_output_path: artifacts/

ACTIONS:
  - PROMPT:
      expert: CTO
      inputs:
        - STR_intro_prompt
        - STR_delimiter
        - 'Write a file called "tech_response.md" detailing your suggested response from the technology team. The output folder should be:'
        - STR_output_path
      output: report01
```

In this workflow:
- We instruct the expert (CTO) to write a file. This will trigger it to use one of its tools, `write_file`.
- We have a named string called `STR_output_path`, and use it to instruct the expert where to create the report file. Our expert will use its `create_directory` tool to create this path.

After this executes, you will see an `artifacts` folder created inside of OWLBEAR, containing `tech_response.md`.


### Example 6: Web Search + Collab

This is a more complex example that shows 3 tool-enabled agents working together.

File: `workflows/sequences/web_research.yml`
```yaml
STRINGS:
  STR_intro_prompt: "We are a financial institution, and we just suffered a major data breach that exposed private data for some of our customers. We need to decide how we respond to this in order to appease customers and regulatory agencies and come up with a response plan."
  STR_delimiter: "*********************************************"
  STR_output_path: artifacts/

ACTIONS:
  - PROMPT:
      expert: CTO
      inputs:
        - STR_intro_prompt
        - STR_delimiter
        - 'Search the web for tips on how best to respond to this data breach incident we are in right now and then create a file "research_summary01.md" that summarizes the key points that you think are most important for the team in order to deal with this incident. Place that file in the following folder:'
        - STR_output_path
      output: websearch01

  - PROMPT:
      expert: "Communication Strategist"
      inputs:
        - STR_intro_prompt
        - STR_delimiter
        - Read the file artifacts/research_summary01.md - this is the CTO's summary of his research on how to deal with the data breach incident we are facing. Read and understand it, and then give your best feedback in order to help him make the best decision.
      output: communication_feedback
  
  - PROMPT:
      expert: "Decision Making Advisor"
      inputs:
        - STR_intro_prompt
        - STR_delimiter
        - Read the file artifacts/research_summary01.md - this is the CTO's summary of his research on how to deal with the data breach incident we are facing. Read and understand it, and then give your best feedback in order to help him make the best decision.
      output: decision_making_feedback

  - PROMPT:
      expert: "CTO"
      inputs:
        - STR_intro_prompt
        - STR_delimiter
        - "Read the file artifacts/research_summary01.md. This is your synthesis on the initial web research you did on how to deal with this incident."
        - STR_delimiter
        - "After reading that, here are feedback from your top two advisors. First, the feedback from your Communication Strategist:"
        - STR_delimiter
        - communication_feedback
        - STR_delimiter
        - "And here is the second feedback, from your Decision Making Advisor:"
        - STR_delimiter
        - decision_making_feedback
        - Based on their feedback and your initial work, please write a final incident response plan to help us deal with this incident. Place it in "artifacts/final_response_plan.md"
      output: cto_final_response
```

In this workflow, the CTO first uses the `brave_web_search` tool to research tips in handling the data breach incident. He writes it to `artifacts/research_summary01.md`.

Then, his two advisors weigh in. The Communications Strategist and the Decison Making Advisor both read the created file using the `read-file` tool, and then they give their feedback to the CTO.

The CTO considers both of their feedback to create a final incident response plan, which he then writes to `artifacts/final_response_plan.md`.

## DECIDE Action
The DECIDE action is a powerful feature in OWLBEAR that enables conditional branching and iterative refinement in workflows. Unlike PROMPT actions which simply request information, DECIDE actions evaluate responses and determine the flow of the workflow based on the decision.

### DECIDE Action Structure

Here's the structure of a DECIDE action:

```yaml
DECIDE:
  expert: "ExpertID"     # The expert making the decision
  inputs:                # Input prompts for the expert
    - "Input 1"
    - "Input 2"
    - "Reference an earlier output"
    - "Ask for TRUE/FALSE decision"
  output: "decision_result"        # Where to store the decision result
  loopback: 2                      # Numeric loopback (1-indexed step number)
  loopback_target: "step_id"       # ID-based loopback (alternative to numeric)
  loop_limit: 5                    # Maximum number of iterations
```

### How DECIDE Actions Work

1. **Decision Format**: The DECIDE action expects the expert to respond with a clear TRUE/FALSE decision. OWLBEAR looks for these keywords in the response.

2. **Decision Extraction**: The action attempts to extract both:
   - A boolean decision (TRUE/FALSE)
   - An explanation/reasoning for the decision

3. **Flow Control**:
   - If TRUE: The workflow continues to the next action
   - If FALSE: The workflow loops back to a previous action

4. **Loopback Mechanisms**: There are two ways to specify where to loop back to:
   - `loopback`: Numeric value specifying the step number (1-indexed) to return to
   - `loopback_target`: String ID referencing a specific action's ID

5. **Loop Protection**: The `loop_limit` parameter prevents infinite loops by setting a maximum number of iterations. If this limit is reached, the workflow will terminate.

### Structuring Expert Prompts for DECIDE Actions

For best results with DECIDE actions, structure your prompts to:

1. **Be Explicit**: Clearly ask for a TRUE/FALSE decision
2. **Provide Context**: Include relevant previous outputs for evaluation
3. **Set Criteria**: Specify the criteria for a TRUE decision
4. **Request Explanation**: Ask the expert to explain their reasoning

Example prompt:
```
Review this response plan:
[Previous output here]

Does this plan meet our requirements for clarity, comprehensiveness, and actionability?
Please evaluate and respond with TRUE if it meets all requirements, or FALSE if we should revise it.
Provide a brief explanation for your decision.
```

### Example: Decision-Making Workflow

Here's an example of using DECIDE to create an iterative refinement loop:

```yaml
ACTIONS:
  - PROMPT:
      id: generate_content
      expert: "Content Creator"
      inputs:
        - "Create a first draft of a blog post about AI ethics."
      output: initial_draft
  
  - DECIDE:
      expert: "Content Editor"
      inputs:
        - "Review this draft blog post:"
        - initial_draft
        - "Is this draft ready for publication? Respond with TRUE if it meets our quality standards, or FALSE if it needs revision."
      output: review_decision
      loopback_target: generate_content
      loop_limit: 3
  
  - PROMPT:
      expert: "Publication Manager"
      inputs:
        - "The following blog post has been approved:"
        - initial_draft
        - "Please format it for publication."
      output: final_output
```

In this workflow:
1. The Content Creator generates an initial draft
2. The Content Editor reviews it and decides if it's ready
3. If FALSE, the workflow loops back to step 1 for revision
4. If TRUE, the workflow proceeds to the Publication Manager

### Numeric vs. ID-Based Loopback

OWLBEAR supports two methods for specifying loopback targets:

1. **Numeric Loopback**:
   ```yaml
   loopback: 2  # Return to the 2nd action in the workflow (1-indexed)
   ```
   Simple but less maintainable as adding/removing actions changes the numbering.

2. **ID-Based Loopback**:
   ```yaml
   loopback_target: "content_generation"  # Return to the action with this ID
   ```
   More maintainable as it refers to actions by name rather than position.

To use ID-based loopbacks, assign IDs to your actions:
```yaml
PROMPT:
  id: content_generation  # This ID can be referenced by loopback_target
  expert: "Expert"
  inputs:
    - "Input"
  output: "output_var"
```

### Best Practices for DECIDE Actions

1. **Clear Decision Criteria**: Make the decision criteria explicit in your prompts
2. **Reasonable Loop Limits**: Set a `loop_limit` appropriate to your workflow
3. **ID-Based Loopbacks**: Use named IDs for better maintainability
4. **Feedback Incorporation**: When looping back, include the previous attempt and feedback

## Creating Custom Complex Actions

Complex Actions allow you to create reusable workflow templates that can be parameterized and used across multiple workflows. This section will guide you through the process of creating your own custom Complex Actions.

### Complex Action Files

Complex Actions are defined in YAML files stored in the `actions/complex` directory. Each file represents a single Complex Action template.

### Basic Structure

A Complex Action definition consists of a sequence of basic PROMPT and DECIDE actions, with variable placeholders:

```yaml
ACTIONS:
  - PROMPT:
      id: first_step_id
      expert: {{expert}}
      inputs:
        - "Fixed prompt text"
        - "Parameterized text: {{variable_name}}"
      output: step1_output
  
  - DECIDE:
      expert: {{expert}}
      inputs:
        - "Review the output:"
        - step1_output
        - "Is this satisfactory? Respond with TRUE or FALSE."
      output: decision_output
      loopback_target: first_step_id
      loop_limit: 3
```

### Variable Placeholders

Use double curly braces `{{variable_name}}` to denote variables that will be replaced when the Complex Action is used:

1. **Standard Variables**:
   - `{{expert}}`: The expert assigned to this Complex Action
   - Other custom variables defined in the `data` section when using the Complex Action

2. **Referencing Outputs**: You can reference outputs from previous steps within the Complex Action, just like in regular workflows.

### Using the Complex Action

To use a Complex Action in a workflow:

```yaml
ACTIONS:
  - COMPLEX:
      action: your_complex_action_name  # Filename without extension
      expert: "ExpertID"                # Expert for all steps in the Complex Action
      data:                             # Custom variables for this instance
        variable_name: "Value to substitute"
        another_variable: "Another value"
      output: final_result              # Output name for the final result
```

### Example: Creating a Comparative Analysis Template

Here's an example of creating a Complex Action for comparative analysis:

1. **Create the file** `actions/complex/comparative_analysis.yml`:

```yaml
ACTIONS:
- PROMPT:
    id: analysis_start
    expert: {{expert}}
    inputs:
      - "I'll conduct a comparison between {{topic_a}} and {{topic_b}}."
      - "First, let me analyze {{topic_a}}:"
      - "{{criteria}}"
    output: topic_a_analysis

- PROMPT:
    expert: {{expert}}
    inputs:
      - "Now, let me analyze {{topic_b}}:"
      - "{{criteria}}"
    output: topic_b_analysis

- PROMPT:
    expert: {{expert}}
    inputs:
      - "Based on my analysis of both {{topic_a}} and {{topic_b}}, here's a comparison:"
      - "Analysis of {{topic_a}}:"
      - topic_a_analysis
      - "Analysis of {{topic_b}}:"
      - topic_b_analysis
      - "I'll compare them based on: {{criteria}}"
    output: comparison_draft

- DECIDE:
    expert: {{expert}}
    inputs:
      - "Review this comparative analysis:"
      - comparison_draft
      - "Is this comparison thorough and balanced? TRUE or FALSE"
    output: quality_check
    loopback_target: analysis_start
    loop_limit: 2

- PROMPT:
    expert: {{expert}}
    inputs:
      - "Final comparison of {{topic_a}} vs {{topic_b}}:"
      - comparison_draft
      - "Recommendation: Based on {{criteria}}, the better option is..."
    output: final_recommendation
```

2. **Use it in a workflow**:

```yaml
ACTIONS:
  - COMPLEX:
      action: comparative_analysis
      expert: "Analysis Expert"
      data:
        topic_a: "Python"
        topic_b: "JavaScript"
        criteria: "performance, readability, ecosystem, learning curve"
      output: language_comparison
  
  - PROMPT:
      expert: "CEO"
      inputs:
        - "Based on this analysis, make a final decision:"
        - language_comparison
      output: final_decision
```

### Best Practices for Complex Actions

1. **Modular Design**: Design Complex Actions to be self-contained and focused on a specific task
2. **Meaningful IDs**: Use descriptive IDs for steps to make loopbacks clear
3. **Clear Variable Names**: Use descriptive variable names that indicate their purpose
4. **Documentation**: Include comments in your Complex Action file explaining its purpose and required variables
5. **Testing**: Test your Complex Action with different variable values to ensure it works as expected

### Advanced Techniques

1. **Nested Variable References**: You can use variables within variables: `"{{prefix}}_{{suffix}}"`
2. **Default Values**: In your workflow implementation, provide default values for optional variables
3. **Conditional Logic**: Use DECIDE actions to create branching logic within your Complex Action

By creating custom Complex Actions, you can build a library of reusable workflow components that make your OWLBEAR implementations more maintainable, consistent, and easier to develop.
