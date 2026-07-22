# Voyager: An Open-Ended Embodied Agent with Large Language Models — Extract (Context)

Source: Wang, Xie, Jiang, Mandlekar, Xiao, Zhu, Fan, Anandkumar. "Voyager: An Open-Ended Embodied Agent with Large Language Models." NVIDIA, Caltech, UT Austin, Stanford, UW Madison. Preprint (arXiv:2305.16291).

This is a condensed verbatim extract containing only the Abstract, a Contribution paragraph from the Introduction, and the Limitations and Future Work section. The full Method section (automatic curriculum, skill library, iterative prompting mechanism), experimental setup, benchmark figures, related work, and appendix are intentionally excluded.

## Abstract

We introduce VOYAGER, the first LLM-powered embodied lifelong learning agent in Minecraft that continuously explores the world, acquires diverse skills, and makes novel discoveries without human intervention. VOYAGER consists of three key components: 1) an automatic curriculum that maximizes exploration, 2) an ever-growing skill library of executable code for storing and retrieving complex behaviors, and 3) a new iterative prompting mechanism that incorporates environment feedback, execution errors, and self-verification for program improvement. VOYAGER interacts with GPT-4 via blackbox queries, which bypasses the need for model parameter fine-tuning. The skills developed by VOYAGER are temporally extended, interpretable, and compositional, which compounds the agent's abilities rapidly and alleviates catastrophic forgetting. Empirically, VOYAGER shows strong in-context lifelong learning capability and exhibits exceptional proficiency in playing Minecraft. It obtains 3.3× more unique items, travels 2.3× longer distances, and unlocks key tech tree milestones up to 15.3× faster than prior SOTA. VOYAGER is able to utilize the learned skill library in a new Minecraft world to solve novel tasks from scratch, while other techniques struggle to generalize.

## Contribution Paragraph

Empirically, VOYAGER demonstrates strong in-context lifelong learning capabilities. It can construct an ever-growing skill library of action programs that are reusable, interpretable, and generalizable to novel tasks. We evaluate VOYAGER systematically against other LLM-based agent techniques (e.g., ReAct, Reflexion, AutoGPT) in MineDojo, an open-source Minecraft AI framework. VOYAGER outperforms prior SOTA by obtaining 3.3× more unique items, unlocking key tech tree milestones up to 15.3× faster, and traversing 2.3× longer distances. We further demonstrate that VOYAGER is able to utilize the learned skill library in a new Minecraft world to solve novel tasks from scratch, while other methods struggle to generalize.

## Limitation or Conclusion Paragraph (Section 4, Limitations and Future Work)

**Cost.** The GPT-4 API incurs significant costs. It is 15× more expensive than GPT-3.5. Nevertheless, VOYAGER requires the quantum leap in code generation quality from GPT-4, which GPT-3.5 and open-source LLMs cannot provide.

**Inaccuracies.** Despite the iterative prompting mechanism, there are still cases where the agent gets stuck and fails to generate the correct skill. The automatic curriculum has the flexibility to reattempt this task at a later time. Occasionally, self-verification module may also fail, such as not recognizing spider string as a success signal of beating a spider.

**Hallucinations.** The automatic curriculum occasionally proposes unachievable tasks. For example, it may ask the agent to craft a "copper sword" or "copper chestplate", which are items that do not exist within the game. Hallucinations also occur during the code generation process. For instance, GPT-4 tends to use cobblestone as a fuel input, despite being an invalid fuel source in the game. Additionally, it may call functions absent in the provided control primitive APIs, leading to code execution errors.

We are confident that improvements in the GPT API models as well as novel techniques for finetuning open-source LLMs will overcome these limitations in the future.
