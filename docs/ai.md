# Using AI, or not

**In short:** you can do everything with the kit without AI. If your community chooses
to use AI for some of the work, this page explains how to keep your knowledge out of the
data AI companies train their models on.

## Working without AI

Every part of the kit is built for people working by hand: entering recordings and
transcripts, writing the model, checking forms, building tables and practice, and
reviewing. Each step has instructions a person can follow and commands a person can run.
No feature needs an AI.

The kit's specs in `knowledge/` were mostly written for and by AI agents, but they're
plain text and a person can read and follow them.

## If you choose to use AI

AI can speed up some jobs, such as reading old handwriting, drafting a first pass at a
model, or finding every example of an ending. It also makes mistakes that look
confident, and it doesn't know your language the way your people do. Treat anything it
produces as a draft for a person to check. The kit marks AI work as AI work, so nobody
mistakes it for a person's decision.

Your community decides whether to use AI at all, for which jobs, and for which material.
By default the kit sends nothing to an AI service. You choose which tiers, if any, may
go to which service.

## Keeping your knowledge out of AI training

AI models learn from huge collections of text gathered from the internet and from what
people type into AI services. Once your knowledge is in a model's training data, there's
no reliable way to take it out. These steps help keep it out.

**Don't publish what you don't want collected.** Anything on a public website can be
collected by companies building AI training sets. Files that say "please don't use this
for training" are a request, and not every collector honours them. For anything
sensitive, the safest choice is not to put it online. Keep it on your own computers or
behind a login only your people have.

**Choose services whose terms don't train on your data, and check those terms
yourself.** AI providers handle your data differently, and their terms change. Before
anyone sends your material to an AI service, find out:

- whether the service uses what you send to train its models,
- whether that is on by default, and how to turn it off,
- how long it keeps what you send, and for what (many keep data for a while to check
  for misuse, even when they don't train on it), and
- whether those terms are in a contract you've agreed to, or only in a settings page
  that could change.

Business and developer accounts often have stronger terms than free personal accounts,
but not always. Read the terms for the account you'll actually use, and write down what
you found and when.

**Turn off training in every account that touches your material.** That includes the
settings of each person's account, not only the organisation's.

**Watch for tools that send text without asking.** Writing assistants, grammar checkers,
translation tools, transcription services, cloud file sync and code editors with AI
features can all send what you're working on to outside servers. Check what's switched
on before opening your material.

**Run models on your own computers where you can.** Some AI models can run entirely on
your own machine, so nothing leaves it. They are usually less capable, but nothing you
put in them goes to anyone else.

**Keep the most sensitive material away from AI entirely.** Restricted tiers are a good
place to draw the line. The kit's default is that no tier goes to an AI service until
your community decides it may.

**Keep a record.** Note which services were used, for what material, under which terms,
and who decided. If a provider's terms change, you'll know what was sent under the old
ones.

None of this is a guarantee. It lowers the risk, and the decisions stay with your
community.
