# ZEZO — My Vision for the Agent System

## 1. My Core Vision

I want ZEZO to work as an intelligent AI orchestrator that understands my requests, plans the work, and assigns tasks directly to the appropriate agents.

I created specialized agents to eliminate the need for ZEZO Coder. Therefore, ZEZO should no longer use ZEZO Coder to perform coding tasks. Its responsibility should be to understand what I want, select the right agent, assign the task, monitor its progress, and report the results.

**ZEZO manages the work. Agents execute the work.**

For example, when I ask ZEZO to build a website, ZEZO should understand that it is a frontend development task, identify an appropriate frontend agent, and assign the task directly to that agent.

The agent should then perform the actual work using its own configured coding tools, such as Antigravity or OpenCode.

## 2. ZEZO Must Understand My Requirements Before Starting a Large Project

Whenever I request a substantial project, such as a website, web application, or full-stack application, I want ZEZO to understand the project before assigning it.

ZEZO should first ask me which technology stack or framework I want to use if that information is not already available. It should also gather enough information about the project to understand what I actually want to build.

Depending on the project, this may include:

- The project's purpose and target audience.
- The required pages, features, and functionality.
- My preferred framework and technology stack.
- The design direction and visual references.
- Any existing files, documents, or project information.
- The expected outcome and deliverables.

ZEZO should not start building a substantial project without understanding its requirements.

It should reuse information I have already provided and ask only the necessary follow-up questions.

Once ZEZO understands the requirements, it should summarize the scope when needed, determine the appropriate workflow, and assign the implementation to the right agent.

## 3. Example: Creating My Portfolio From My Resume

Suppose I tell ZEZO:

"Read my resume and create a portfolio website."

I want ZEZO to follow this process:

1. Read my resume and understand my experience, skills, projects, and achievements.
2. Identify the information needed to create my portfolio.
3. Ask me relevant questions about the website's design, structure, framework, features, and other important requirements.
4. Understand and confirm the project requirements before proceeding.
5. Identify the most suitable agent for the work.
6. Assign the portfolio development task directly to that agent.
7. Let the assigned agent build the portfolio using its configured coding tools.
8. Monitor the task and tell me its actual progress and status.
9. Once the work is finished, provide the correct project location and verified results.

I want ZEZO to act as the project manager throughout this process, not as the developer performing the coding work itself.

## 4. ZEZO Must Automatically Select the Right Agent

I do not want to manually specify an agent every time I assign a task.

ZEZO should understand the type of work required and select an appropriate agent from the available agent list based on that agent's configured responsibilities, capabilities, tools, and availability.

For example:

- **Ali — Frontend Development:** Website designs, landing pages, and frontend implementation.
- **Haider — Frontend Development:** Frontend tasks when Ali is at capacity, provided Haider is available and suitable.
- **Ahmad — Full-Stack Development:** Full-stack applications and related work when his configured capabilities match.
- **Other specialized agents:** Tasks that match their respective skills and configured tools.

These are examples of how I want the system to work, based on the agents I have configured.

ZEZO should inspect the available agents, choose the most appropriate one, and assign the task directly to that agent.

If an agent is already at its maximum capacity, ZEZO should look for another suitable agent instead of automatically sending the work to ZEZO Coder.

## 5. Agents Must Handle Multiple Tasks Simultaneously

I want each agent to be capable of handling multiple tasks at the same time, up to its configured concurrency limit.

The default maximum I want is **three concurrent tasks per agent**.

For example, suppose I assign these tasks:

- Create a portfolio website.
- Create a business landing page.
- Create a dental landing page.

ZEZO should be able to assign all three tasks to Ali if he is eligible and has the capacity. Ali should be able to work on all three tasks concurrently, provided his configured execution environment supports it.

Now suppose I assign a fourth website task while Ali is already handling three active tasks.

ZEZO should recognize that Ali has reached his limit. It should then check the available agents and assign the fourth task to Haider if he is suitable and has available capacity.

If no suitable agent is available, ZEZO should handle the task according to the configured queue policy.

I want ZEZO to distribute work intelligently rather than allowing one agent to exceed its limit while other suitable agents remain available.

## 6. Every Independent Project Must Have Its Own Folder

I want every independent project to have its own separate working directory.

This is extremely important to me because I may assign multiple website projects at the same time, and each agent must work only inside the directory assigned to its particular project.

For example, if I select my Desktop as the base location, ZEZO should automatically create separate project folders:

```text
Desktop/
├── hamza-portfolio/
├── real-estate-landing-page/
├── dental-landing-page/
└── business-landing-page/
```

Each folder should contain the files and assets belonging to its respective project.

The folder names are examples; the system can generate appropriate names automatically.

### How I want this to work

- When I assign a new independent project, ZEZO should create or allocate a dedicated project folder.
- The assigned agent should receive that project's exact working directory.
- Each agent must work within its assigned project directory.
- Multiple agents and tasks must not accidentally write their files into the same project folder.
- Different projects may share the same parent directory, such as my Desktop, but they must have separate project directories.
- ZEZO must not reuse a previous project's folder for an unrelated new project.
- If I intentionally ask an agent to continue working on an existing project, it should use that project's existing folder.
- Browser previews must open the correct project's files.

For example, the real-estate website, my portfolio, and the dental website must remain completely separate projects, even if they are created simultaneously.

**Every independent project must have its own isolated workspace, regardless of which agent builds it.**

## 7. I Want Clear Task Ownership and Status

Whenever ZEZO assigns work, I want to know which agent is responsible for that task.

For example, if Ali is building my portfolio, the task manager should show that Ali owns and is working on the portfolio task. It should not show ZEZO Coder as the task owner.

I want ZEZO to provide accurate information about:

- Which agent owns each task.
- Which tasks are currently running.
- Which tasks are waiting in the queue.
- Why a task is queued, when applicable.
- Which tasks have completed or failed.
- Which project folder belongs to each task.
- Which files have actually been generated.
- Whether a task encountered an error or required a retry.
- Where I can access the completed project.

ZEZO should not invent progress percentages or claim that work is complete just because a task was dispatched or a coding tool was launched.

When I ask for a task's status, ZEZO should report the status of the existing task rather than creating another task.

If a task needs to be retried, ZEZO should retain its relationship to the original task.

## 8. My Expected Overall Workflow

The complete workflow I want is:

**Understand → Clarify → Plan → Select Agent → Allocate Project Folder → Assign Task → Execute → Verify → Report**

1. **Understand:** ZEZO understands what I want to accomplish.
2. **Clarify:** It asks the necessary questions for substantial projects.
3. **Plan:** It determines the required work and expected deliverables.
4. **Select Agent:** It identifies the most suitable available agent.
5. **Allocate Project Folder:** It creates or identifies the correct isolated workspace.
6. **Assign Task:** It dispatches the task directly to the selected agent.
7. **Execute:** The assigned agent performs the work using its configured coding tools.
8. **Verify:** ZEZO checks the actual task status, output files, and project location.
9. **Report:** ZEZO tells me which agent handled the task, what was completed, and where the deliverables are located.

## 9. The Final Outcome I Want

I want ZEZO to function as an intelligent manager of my agent system.

I should be able to describe what I want in natural language without having to manually choose a coding tool, manage every agent assignment, or organize project folders myself.

ZEZO should understand the request, gather the necessary requirements, select the right agent, distribute work according to agent availability, create isolated workspaces, and monitor execution.

The agents should perform the actual development work through their configured tools. ZEZO should coordinate everything and report verified results.

My goal is to have a system where multiple agents can work on different projects simultaneously without exceeding their individual task limits or interfering with one another's files.

**In short: I want ZEZO to be the intelligent orchestrator, my agents to be the actual workers, and every independent project to have its own isolated workspace.**