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
To run one of the sample workflows:
```bash
python3 owlbear.py workflows/databreach.yml
```
In this simple example, 3 experts work together to create a data breach response plan:
- CEO
- Strategic Thinking Partner
- Ethical Decision Making Counselor

After that runs, you can view the outputs in the `outputs/databreach_[timestamp]/` folder

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
python3 owlbear.py workflows/helloworld.yml
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
python3 owlbear.py workflows/test.yml
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

File: `workflows/databreach.yml`
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

### Example 4: Data Breach Response Plan Collaboration
In this simple example, we have only one expert, but it will use tools to create a report file directly instead of just having it in its text response.

File: `workflows/report_creation.yml`
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


### Example 5: Web Search + Collab

This is a more complex example that shows 3 tool-enabled agents working together.

File: `workflows/web_research.yml`
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