# Beginner handover pack

Give the tester [Automotive-CAD-Copilot-Handover.pdf](Automotive-CAD-Copilot-Handover.pdf) for reading or the editable [Automotive-CAD-Copilot-Handover.docx](Automotive-CAD-Copilot-Handover.docx). Both contain the same detailed instructions. Start at section 1 and follow the Mac setup before sending requests through Codex.

- `guide.md`: source instructions with copyable command blocks. On GitHub, use the code-block copy button. In a plain text editor, copy the block contents without backticks.
- `results-template.csv`: ten blank conversational scenario records. Open in Excel, Numbers or another CSV editor. Fill in observed results; do not change the expected-result column.
- `tester-notes-template.txt`: environment, walkthrough, checks and defect-report form. Make a copy in your dated evidence folder and fill it in.

Download the actual application code from https://github.com/vinayanand3/automotive-cad-copilot. The handover pack does not install FreeCAD, Python or Codex. The tested platform is macOS Apple Silicon with FreeCAD 1.1.3 and Python 3.10 or newer for the CLI. Other platforms remain unverified.

The guide is based on implementation revision `a60657a`. Documentation additions can have a later commit; record the checkout you actually test. Historical passing tests in the repository are reference evidence, not the recipient's results.

Return the completed forms, dated test outputs and relevant model folders as described in section 18. Do not send credentials or the full computer environment.
