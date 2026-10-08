---
layout: post
title: "Milestone 1: Solving Slay the Spire 2 at Ascension 0"
date: 2026-10-07
author: Shawn Xu
math: true
---
This is a write up of my personal project: Building an AI to play Slay the Spire 2. Building autonomous AI agents to play games has always been a hobby of mine, and in the past I've made AIs to play chess, poker, scrabble, RTS video games, and various other projects. Another motivation is that I wanted to gauge how well frontier LLM agents can (largely) navigate an open machine learning problem such as this one (my day job involves training LLM agents at one of the frontier labs). I've used Claude and Gemini extensively in this project as research partners and coders. However, note that I am not interested in using an LLM *itself* to act as the game agent, even though they will eventually get there. Instead, this project aims at using LLMs to build a *small* game AI.

I started this project in March 2026. When I started, "solving" STS2 still seemed out of reach beyond my wildest imagination. Sts1 has been out for 7 years and many AI attempts have been made, but none was convincing. I was inspired to post this after seeing [Jorb's recent post](https://www.reddit.com/r/slaythespire/comments/1vxfsf4/jorbs_actually_built_a_fight_solver_for_sts_2/).


*Headline first*: The autonomous agent now wins about 87% of Ironclad runs at Ascension 0, up from about 10% in August 2026. I consider A0 effectively solved and am declaring Milestone 1 complete.

*Important caveat*: This AI does "cheat" via "save scumming". The game engine is identical to the real game, including all deterministic rollouts, so the agent knows exactly what cards will be drawn the next turn, etc. Technically, humans have access to this information as well, via save scumming. This was an early decision -- I wanted to make the problem easier first. Future milestones will aim at removing this extra information.

## The result

<figure>
{% include figures/winrate.svg %}
  <figcaption>Fleet A/B tests, Aug 28 – Oct 7 2026; promoted arm of each test, about 1,000 seeds per arm. Hover a point to see the change it shipped.</figcaption>
</figure>

Three ideas account for most of the climb: choosing events by their measured effect on winning, simulating each fight before playing it, and the turn beam. Every point is a change that won a paired test against the agent before it.

## How it works

The agent is a stack of separate components: combat is solved by search, and the run-level decisions use learned models plus search over the map. No component is hand-scripted for specific fights.

**Combat**

- **Combat search agent.** A 3-turn lookahead search over card plays, targets and card-selection prompts, run inside an exact copy of the game engine. It branches on every meaningful choice and undoes moves with an undo log.
- **Learned leaf evaluation.** A [gradient-boosted](https://en.wikipedia.org/wiki/Gradient_boosting) model predicts the HP the player will end the fight with, from the board state (hand, piles, powers, enemy intents, potions). Search uses it to score positions three turns out.
- **Playout gate.** At the start of each fight, the agent plays the whole fight out in simulation with its default strategy. If that playout dies, it tries a ladder of alternative strategies (deeper search, racing the enemy, drinking potions) and adopts the first one that wins. The winning line is cached and replayed turn by turn.
- **Turn beam.** The last rungs of that ladder. Instead of committing to one plan per turn, it keeps the best 40 to 80 end-of-turn positions alive across turns. This finds setup turns and burst windows that look bad in the short term, which the per-turn search prunes away. Three score variants (racing, scaling, wider) cover fights the default misses.

**Between fights**

- **Act path planner.** A beam search over the act's map that forks the engine to simulate each route's fights, rests, shops and events. It scores routes by a learned estimate of surviving the act and the bosses after it, and replans every floor.
- **Forkrank (card picks).** A ranking model trained on counterfactuals. For each card reward, the run is forked and continued with each option, and the model learns which pick actually leads to wins. It takes over card picks from floor 17 on.
- **Event table.** For each event option, the causal effect of taking it on winning, estimated from forked continuations of the first step only.
- **Shop, potions and rest.** Learned shop picks with a rule that buys affordable relics over cards, card removal of the weakest card, and rule-based potion use (for example, defensive potions only when the next hit is lethal).

<figure>
  <img src="{{ '/assets/img/architecture.svg' | relative_url }}" alt="Learned models plan the run; search plays each fight">
  <figcaption>Agent architecture: four run-level components, a four-step fight pipeline, and the shared simulator.</figcaption>
</figure>

Every component queries the same simulator: the planner forks the run to try routes, forkrank forks it to try card picks, and the fight pipeline plays whole fights out before committing.

## The math behind it

Both halves of the agent search a model of the game: combat searches the exact game with a learned value at the leaves, and the run-level planner searches routes scored by learned survival probabilities.

### Combat: deterministic search with a learned leaf value

A fight is a sequence of states $$s$$ and actions $$a$$ (play card $$i$$ on target $$j$$, drink a potion, end the turn). The simulator gives the next state, $$f(s, a)$$, including the enemies' moves. Because it reproduces the game's random number generator exactly, the search treats each fight as deterministic. The objective is the HP the player ends the fight with.

The default policy looks three turns ahead and picks the action sequence whose end state scores highest:

$$
a^{*} = \arg\max_{\pi \in \Pi_{3}(s_0)} \hat{V}\big(s^{\pi}\big), \qquad
\hat{V}(s) = \begin{cases} \mathrm{HP}(s) & \text{fight won} \\ -\infty & \text{player dead} \\ \mathrm{HP}(s) + g_{\theta}(\phi(s)) & \text{otherwise} \end{cases}
$$

Here $$\Pi_3(s_0)$$ is the set of action sequences covering the next three turns, $$\phi(s)$$ is a feature vector of the board (hand, piles, powers, enemy intents, potions), and $$g_\theta$$ is a [gradient-boosted tree](https://en.wikipedia.org/wiki/Gradient_boosting) model trained to predict the HP still to be lost, $$\mathrm{HP}_{\text{final}} - \mathrm{HP}(s)$$. The search re-plans every turn.

**Playout gate.** Before the first turn, the agent plays the entire fight out under an ordered list of strategies $$\sigma_1, \dots, \sigma_K$$. Each playout returns whether it won, the final HP and how many turns it survived. The agent adopts the first strategy that wins (or, if none does, the one that survived longest) and replays its line turn by turn:

$$
k^{*} = \min\{\, k : \mathrm{won}(\sigma_k) \,\}
$$

**Turn beam.** The last strategies in the list replace one-plan-per-turn with a beam over end-of-turn states. $$B_t$$ holds the $$W$$ best states after turn $$t$$; each is expanded by every distinct full turn $$\tau$$ (a sequence of plays ending in end turn):

$$
B_{t+1} = \operatorname{top}_W \big\{\, f(s, \tau) : s \in B_t,\ \tau \in \mathcal{T}(s) \,\big\}, \qquad
h(s) = 3\,\mathrm{HP} - \sum_{e}(\mathrm{HP}_e + \mathrm{Block}_e) + 8\,\mathrm{Str} + 6\,n_{\mathrm{buffs}} + 20\,n_{\mathrm{dead}}
$$

The score $$h$$ is deliberately simple and needs no learned model. Its variants reweight it: less weight on HP to race the enemy, more weight on Strength and buffs to scale, or a wider beam.

### Between fights: planning against learned survival probabilities

The run-level objective is the probability of winning the run. The act path planner runs a beam search over routes $$p$$ through the act's map (beam width 32) and scores each route roughly as

$$
J(p) = \prod_{r \in p} \Pr\big(L_r < \mathrm{HP}_r\big) \cdot \prod_{b \in \text{future bosses}} q_{\psi}\big(b,\ \mathrm{deck}_{\text{end}},\ \mathrm{HP}_{\text{end}}\big)
$$

$$L_r$$ is the HP lost in room $$r$$, with its distribution per encounter estimated from past fights (censored Kaplan–Meier curves). $$q_\psi$$ is a learned model of beating a future boss with a given deck and HP. The planner simulates each route's rooms in a fork of the engine, and replans every floor.

**Forkrank.** At a card reward with options $$c_1, \dots, c_m$$, the run is forked once per option and played to the end, giving a win label $$y_c$$ for each. A scoring model $$r_\omega$$ is trained on pairs where the outcomes disagree, with a pairwise logistic (RankNet) loss, and the agent picks the highest-scoring option:

$$
\mathcal{L}(\omega) = -\sum_{(i,j)\,:\,y_i > y_j} \log \sigma\big(r_{\omega}(x, c_i) - r_{\omega}(x, c_j)\big)
$$

**Event table.** For each event and option, the table stores the estimated effect of choosing that option on the chance of winning, measured by forking the run at the event and continuing with each option. Only the event's first step is used, which avoided push-your-luck chains that looked good on average but lost runs.

### Future direction: playing with only what a player can see

Everything above searches the exact engine, random number generator included. Inside a search, the agent therefore knows things a human player cannot: the order of the draw pile, which cards a potion or event will generate, and the enemies' moves beyond the intent shown for the next turn. A natural next step is an agent that plays with only the information a real player has, which also makes the comparison with human play fair.

Formally, a fight becomes a partially observable problem. The player sees an observation $$o$$: the hand, the contents (but not the order) of the draw and discard piles, HP, powers, potions, and each enemy's current intent. The true state $$s$$ adds the hidden part, mainly the generator's state. The agent keeps a belief $$b(s \mid o)$$ over the states consistent with what it has seen.

The simplest change is **determinization**: sample $$K$$ plausible worlds from the belief (shuffle the draw pile, reseed the generator, keep everything observed), search each one with the existing engine, and pick the action that does best on average:

$$
a^{*} = \arg\max_{a} \; \frac{1}{K} \sum_{k=1}^{K} \hat{V}\big(f_k(s_k, a)\big), \qquad s_k \sim b(\,\cdot \mid o)
$$

Each component would change accordingly:

- **Combat search** turns end-of-turn draws into chance nodes. Searching each sampled world separately is cheap to build but can assume it will know the future once it gets there. Searching over information sets, so that one plan has to work across all the worlds (information-set Monte Carlo tree search), fixes that at a higher cost.
- **The leaf evaluation** needs no retraining in principle. Its features are mostly observable already; the hidden draw order would be removed.
- **The playout gate** can no longer adopt the first strategy that wins one deterministic playout. It would play each strategy out in $$K$$ sampled worlds, adopt the one with the highest estimated chance of winning, $$\hat{p}(\sigma) = \tfrac{1}{K}\sum_k \mathrm{won}_k(\sigma)$$, and re-plan every turn instead of replaying a cached line.
- **The turn beam** would score each end-of-turn state by its average over sampled worlds, so a setup turn survives only if it pays off in most of them.
- **Between fights**, the planner and forkrank also fork the true engine and see future card rewards and event outcomes. They would sample those futures too; forkrank's training labels would come from many continuations per option rather than one.

The cost is roughly $$K$$ times more compute per decision, and some loss of win rate from no longer knowing the future. Measuring that gap with the same paired A/B tests would tell us how much of the 87% depends on hidden information, and how much an honest agent can recover.

### Deciding what ships

Each change runs against the current agent on the same 1,000 seeds. With $$b$$ runs rescued (new wins) and $$c$$ runs thrown (new losses), it ships when a continuity-corrected McNemar test is significant and it still comes out ahead with unfinished runs counted as losses:

$$
\chi^2 = \frac{\big(\lvert b - c\rvert - 1\big)^2}{b + c}
$$

## Timeline of the big jumps

The biggest gains came from changing what the agent optimizes or how it chooses, not from searching deeper. Each step below shipped only after a paired A/B test on 1,000 seeds per arm; the lift is the win-rate gain over the agent it replaced.

| Shipped | Idea | Win rate (before → after) |
| --- | --- | --- |
| Oct 7 | **Turn-beam variants**: racing, scaling and wider beams for fights the default beam misses | 83% → 87% |
| Oct 7 | **Turn beam**: keep many end-of-turn positions alive, so setup turns survive until they pay off. Distilled from how Claude won fights the agent had lost | 76% → 82% |
| Oct 4 | **Strict defensive potions**: drink block or healing potions only when they prevent a lethal hit | 74% → 78% |
| Sep 29 – Oct 2 | **Playout gate**: simulate each whole fight before playing it, switch strategy if the default dies; later added potion and racing fallbacks and a replay cache | 57% → 74% |
| Sep 28 | **Relics over cards in shops** | 42% → 47% |
| Sep 24 | **Consistent picks**: the map planner uses the same pick model the agent plays with | 45% → 50% |
| Sep 23 | **Causal event table**: choose event options by their measured effect on winning | 36% → 53% |
| Sep 16 – 22 | **Forkrank**: learn card picks from forked counterfactual runs, then retrain on the agent's own runs | 22% → 34% |
| Sep 10 | **Potion-aware leaf evaluation** | 23% → 24% |
| Aug 29 – 30 | **Survival-based route planning**: replan every floor, score routes by the chance of surviving the act and future bosses | 10% → 19% |

Each A/B used its own seed pool and the agent kept improving between tests, so the "before" of one row does not exactly match the "after" of the previous one. Earlier work (June to August) built the simulator, the combat search and the first learned models; it moved the agent from dying mid-act to reaching bosses.

## What made it possible

Three pieces of infrastructure carry everything above.

- **A headless simulator built from the game's own code.** The game's logic is compiled directly, with the graphics and audio stubbed out, so the agent searches in the real rules rather than a reimplementation. It runs fully deterministically, which lets the agent fork a run, try every option, and rewind.
- **Parity checking against the real game.** Recorded runs from the live game are replayed step by step in the simulator and compared state by state. About 1,300 recorded runs replay cleanly, and a separate check confirms that what the search predicts matches what actually happens when the plan is played.
- **Fleet A/B testing.** Every change is tested on a cluster against the current agent on 1,000 fresh seeds per arm, paired by seed. It ships only if it wins significantly and still comes out ahead when unfinished runs are counted as losses. This kept us from shipping ideas that looked good on a handful of seeds, and caught one test that ran on a broken setup.

Claude also worked as an offline teacher. It played fights the agent had lost, through a step-by-step interface into the simulator. Its winning lines showed which strategies were missing, and the turn beam turned the most common one into an automatic search.

## What's next

About 13% of runs are still lost, half of them at the final boss. The open problems:

- **Removing save scumming.** Future milestones will only be published if the agent wins without knowing the random rollouts.
- **Entry HP into bosses.** Arriving with 10 more HP turns about a third of the fights we lose into wins. We are testing a gate that picks the line that keeps the most HP in ordinary fights before a boss.
- **Teaching the leaf evaluation.** The turn beam's winning lines can train the evaluation model, so the everyday search finds these lines without the slow fallback.
- **Higher Ascensions and other characters.** Milestone 1 covers the Ironclad at Ascension 0. Higher Ascensions add harder enemies and fewer resources, and the other characters need their own card knowledge.
