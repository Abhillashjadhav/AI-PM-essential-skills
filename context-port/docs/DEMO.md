# Synthetic migration demonstration

Run the complete safe ContextPort pipeline from the public checkout:

```sh
python3 context-port/demo.py
```

The demo uses only committed synthetic fixtures. It validates a ContextPack, preserves project segregation, verifies a canned synthetic approval artifact, builds a reconstruction dry run, independently reconciles it, and assesses the ChatGPT destination capability.

The final stage is intentionally `UNSUPPORTED`: no public consumer ChatGPT reconstruction write interface has been verified. Every planned operation is reported as not copied. The demo performs no account access, network call, browser automation, or destination write.

The report binds itself directly to the checkout's exact Git `HEAD`; it accepts no revision override. It records completed stage exit states, source artifact and inventory digests, stable stage digests and counts, an explicit unobserved destination inventory, per-operation dispositions for everything not copied, environment limitations, and a digest over the complete report.

- `VERIFIED`: demonstrated by completed checks over synthetic fixtures;
- `UNKNOWN`: real Claude export compatibility, pending separately approved inspection;
- `UNSUPPORTED`: ChatGPT reconstruction writes.

This is evidence for the synthetic migration MVP only. It is not evidence that a real Claude ZIP has been parsed or that content has been written to ChatGPT.
