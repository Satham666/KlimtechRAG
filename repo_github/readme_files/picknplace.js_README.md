# picknplace.js

A proof of concept of a viable drag and drop alternative.

<a href="https://jgthms.com/picknplace.js/"><img width="1200" height="630" alt="facebook" src="https://github.com/user-attachments/assets/321c7c2f-c523-408d-884a-d87c4cb9130f" /></a>

### Why?

I find that the drag and drop experience can quickly become a nightmare, especially on mobile.
Trying to tap, hold, drag, and scroll, all at the _same time_, is awkward, slow, and error-prone.
I've long had in mind a simpler 2-step approach: picking an item first, _then_ placing it.
So I implemented this basic version to showcase my idea.

### How it works

When picking an item, a duplicate of the list is created on top of the original one.
The duplicate is interactive and animated, and will update based on the scroll position.
At the end, the user can either confirm or cancel the changes.

### Is this a library?

Not exactly. This is merely a proof of concept, to convey what I had in mind.
You can however look at the source code, for inspiration.
