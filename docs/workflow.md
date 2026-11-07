# How the kit works

**In short:** your community's recordings and your model of the language are kept
apart and compared. Everything else, from tables to practice and checking new
sentences, comes from that comparison, and always says where it came from.

lect-kit is still being built. This page describes the design, which comes from a
project already working this way.

## The big picture

There are two sides, kept apart on purpose.

- **The record** is what speakers said, as it was recorded. It is never changed to suit
  anyone's theory.
- **The model** is a description of how the language builds its words. It's your
  community's best current understanding, and it can be wrong.

The kit lines the two up. Where the model predicts a word that the record holds, that's
a match. Where it predicts something nobody recorded, or the record holds something the
model can't explain, that's worth a closer look. The model might be wrong, the
transcription might be wrong, or nobody happened to record that word.

Because the two sides are built separately, those gaps mean something. Nobody arranged
for them to match.

## 1. The record

Each recording or written source has a page of its own with the text and the details
around it:

- **When** it was recorded or written, and **where**.
- **Who spoke**, and which language or dialect they spoke.
- **Who recorded or wrote it down.**
- Its **classification**, and the parts of it classified differently.

These details are filled in as well as the source allows. Each one says how it's known:
from the source itself, by inference, or from family or community. Where records
disagree, both are kept. Where something isn't known, it's left empty rather than
guessed.

When a recorder got something wrong, such as a translation, a spelling or where one word
ends and the next begins, the correction goes beside the original with a date and a
reason. The original stays as it was.

## 2. The model

The model lists the words of the language and the ways they change, for example which
endings a verb takes and in what order they can stack. From that, the kit works out
every form the model predicts.

Each predicted form keeps a note of the rules that made it, so when a form looks wrong
you can see which rule to fix.

## 3. Comparing them

The kit checks every predicted form against the record, in the same language or
dialect. A form is either:

- **recorded**, with a link to who said it and when,
- **built** by the model but not recorded, or
- **not predicted**, because the model doesn't produce it.

Only a person can say a form is genuinely unrecorded after looking, and the kit never
calls any form wrong.

The kit also counts how well the model fits the record. By default it won't accept a
change that makes the fit worse, though a person can decide otherwise.

## 4. Tables

The first thing the kit produces is tables of word forms, like conjugation tables.
Recorded and built forms look different. Click a recorded form to see the sentence it
came from, who said it, and when. Click a built form to see how the model made it. Every
table says which version of the record and model it came from.

## 5. New sentences for learners

Learners need sentences nobody was recorded saying. The kit allows that, carefully. Each
new sentence borrows its shape from a real recorded sentence. The kit then checks every
word and marks it:

- **recorded** in that language or dialect,
- **built** by the model, or
- **unplaced**, in which case the sentence isn't published by default.

Passing these checks means every word is accounted for. It doesn't mean a speaker would
say the sentence, or that it means exactly what its translation says. Those still need a
person.

## 6. Practice

Practice items come only from material that has passed the checks above. Every item
tells the learner where the answer came from: recorded (and by whom), built from the
model, or a new sentence. A learner can choose to practise recorded forms only.

When a learner gives a form from a neighbouring dialect, or divides the word in a
different place, they get feedback that says so instead of a plain "wrong".

How and with whom practice is used is each community's decision.

## 7. Checking a sentence

Anyone can give the kit a word or sentence and see, word by word:

- which forms in the model build it,
- how often it appears in the record, and where,
- or that the kit can't account for it.

There's no score and no verdict. A word the kit can't place might still be good
language, because the record and the model are both incomplete. The report shows what
supports each word, and people make the judgement.
