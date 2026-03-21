# WiSpec — Legal Notes: What Is Enforceable vs. What Is Wishful Thinking

**Disclaimer: I am not a lawyer. This document is my best understanding as a researcher. Get actual legal counsel before relying on any of this for real money or real disputes.**

---

## The Licensing Landscape: Key Distinctions

### Open Source
A license approved by the Open Source Initiative (OSI). Examples: MIT, Apache 2.0, GPL, BSD. Key property: **anyone can use it for any purpose, including commercial**, subject to the license conditions (attribution, copyleft, etc.). You cannot restrict commercial use and call it open source. The term "open source" has a specific legal and community meaning.

### Source-Available
Code is publicly visible (e.g., on GitHub) but the license restricts certain uses — typically commercial use. Examples: Business Source License (BSL), Commons Clause, Server Side Public License (SSPL), Elastic License 2.0. **This is what WiSpec uses.** The code is readable and usable for research, but commercial use requires a separate agreement.

### Noncommercial Academic License
A source-available license specifically designed for academic research contexts. Permits research and education, requires citation, prohibits commercial use. Common in academic software (e.g., many university-developed tools use similar terms). Creative Commons has a well-known noncommercial variant (CC BY-NC), but CC licenses are designed for creative works, not software — using CC for code is discouraged by Creative Commons themselves.

### Dual Licensing / Separate Commercial License
The same code is available under two licenses: a free noncommercial license for researchers, and a paid commercial license for companies. This is the model used by Qt, MySQL (historically), and many academic tools. **This is the model WiSpec follows.**

---

## What IS Enforceable (High Confidence)

### 1. Copyright on Your Code
You wrote the code. You own the copyright. This is automatic under U.S. law (no registration required, though registration strengthens enforcement). **Nobody can copy, distribute, or create derivative works without your permission**, except as you grant in your license. This is the bedrock of everything.

### 2. Restricting Commercial Use via License
Noncommercial licenses are legally recognized. The Artistic License, CC BY-NC, and various academic licenses have been upheld or at least taken seriously in legal contexts. If someone uses your code commercially without a license, they are infringing your copyright. You can send a DMCA takedown (if they host infringing code) or sue for copyright infringement. **Practically enforceable? Yes, if you can detect the infringement and are willing to act.**

### 3. Requiring Attribution
Attribution requirements in licenses are standard and enforceable. MIT, Apache, BSD, and CC all require attribution. Courts have upheld attribution requirements. If someone strips your name off and publishes your work, that is both a license violation and potentially plagiarism. **This is your strongest and most practically enforceable term.**

### 4. Requiring Citation in Academic Work
Academic citation norms are enforced by the academic community itself (journals, conferences, peer reviewers) more than by courts. If someone publishes a paper using your code without citing you, the most effective remedy is: (a) contact the journal/conference, (b) file a complaint with the authors' institution, (c) post publicly about it. **Courts probably won't sue over a missing citation, but the academic community will enforce it.** Making citation a license condition adds legal weight — it transforms a norm violation into a license violation (and thus a copyright infringement).

### 5. Termination Clause
If someone violates your license, their right to use the code terminates automatically. This is standard and enforceable. They would then be using your code without any license, which is straightforward copyright infringement.

---

## What Is PARTIALLY Enforceable (Medium Confidence)

### 6. Defining "Noncommercial" vs. "Commercial"
The boundary between noncommercial and commercial use is famously fuzzy. Is a university research project funded by a defense contractor noncommercial? Is a startup using your code for internal prototyping commercial? Courts have grappled with this (see the Creative Commons litigation history). **Your license defines these terms, which helps, but edge cases will always exist.** The clearer your definition, the better.

### 7. "Source-Available" License Enforcement Against Large Companies
If a large company uses your code without a commercial license, you have legal grounds (copyright infringement). But enforcement requires: (a) detecting the infringement, (b) having resources to send a credible legal letter, (c) potentially litigating. **Practically, small individual developers rarely sue large companies.** However, the threat of legal action plus reputational damage often motivates companies to comply. Having a clear license and a paper trail (the COMMERCIAL-LICENSING.md file) strengthens your position.

### 8. Governing Law Clause
You specified Arizona law. This is enforceable for disputes in U.S. courts. But if a company in another country infringes, enforcing Arizona law is impractical. **Domestic enforcement: good. International enforcement: difficult.**

---

## What Is NOT Enforceable via Repo License Alone (Low Confidence / Needs Separate Contract)

### 9. Royalties / Revenue Share
**A repo license file CANNOT create an enforceable royalty obligation.** Royalties require:
- A signed contract (not just a license file someone read on GitHub)
- Specific payment terms (percentage, payment schedule, audit rights)
- Definition of "revenue" or "net revenue" (gross? after costs? which costs?)
- Audit rights (how do you verify what they earned?)
- Dispute resolution mechanism
- Signatures from authorized representatives

A GitHub license file is a unilateral grant — the user never signs anything. Courts generally require mutual assent (offer + acceptance) for financial obligations like royalties. **If you want royalties, you MUST have a separately negotiated and signed commercial license agreement.** The COMMERCIAL-LICENSING.md file is a starting point for that negotiation, not a binding royalty agreement.

### 10. Downstream Revenue Tracking
Even with a signed contract, tracking downstream revenue is extremely difficult. If a company uses your material classification method inside a larger product, what fraction of their revenue is attributable to your code? **This is why most commercial software licenses use flat fees or per-seat pricing rather than revenue share.** Revenue share works in some industries (music, publishing) because there are established tracking mechanisms. Software generally lacks these.

### 11. Preventing Ideas from Being Used
Copyright protects expression (your specific code), not ideas or methods. If someone reads your paper, understands the dual-band differential attenuation approach, and writes their own code from scratch implementing the same idea, **your copyright does not cover that.** They haven't copied your code; they've implemented a method described in a scientific paper. To protect ideas/methods, you would need a **patent** — which is expensive ($10K–$15K+ to file) and has its own enforceability challenges.

### 12. Preventing Re-Implementation
Related to the above: if your paper describes the algorithm clearly enough that someone can re-implement it, your license on the code doesn't prevent that re-implementation. **This is fundamental to how science works — published methods are meant to be reproducible.** Your license protects your code and your datasets, not the underlying scientific concepts.

---

## Practical Recommendations

### What You Should Do Now
1. **Keep the noncommercial source-available license** (LICENSE.md). It's appropriate and defensible.
2. **Keep the CITATION.cff** file. GitHub renders it into a cite button automatically.
3. **Register your copyright** with the U.S. Copyright Office ($65 online, copyright.gov). This is optional but gives you statutory damages and attorney's fees in infringement cases, which makes enforcement much more credible.
4. **Consider a provisional patent application** if you believe the dual-band differential method has commercial value. A provisional patent costs ~$200 to file yourself and gives you 12 months of "patent pending" status while you decide whether to pursue a full patent. **Talk to ASU's technology transfer office (Skysong Innovations) — they may file it for free if they see commercial potential.**
5. **When a company contacts you for commercial use**, have a lawyer draft the actual commercial license agreement. Do not try to write a royalty contract yourself.

### What You Should NOT Do
1. **Don't call it "open source."** It isn't. Say "source-available" or "noncommercial license." The open-source community takes terminology seriously and you'll lose credibility if you mislabel it.
2. **Don't use a Creative Commons license for code.** CC licenses are designed for creative works (text, images, music), not software. CC themselves recommend against it.
3. **Don't assume the license prevents all misuse.** Some people will ignore licenses. Your protection is copyright law, not the honor system.
4. **Don't put royalty terms in the license file.** They won't be enforceable and they'll make the license look amateurish.

### When You Need a Real Lawyer
- Before signing any commercial license deal
- Before filing a patent application (provisional is okay solo, full patent needs a patent attorney)
- If you discover a company using your code commercially without permission
- If ASU's technology transfer office (Skysong Innovations) gets involved — they will have their own lawyers
- If you receive funding that has IP obligations attached (some grants require open-source release)

---

## ASU-Specific Considerations

**Important:** If you developed this code as part of your coursework or with ASU resources (lab equipment, computing, FURI funding), ASU may have IP claims under their intellectual property policy. Specifically:

- **FURI-funded work:** Check whether FURI's terms include an IP assignment clause. Many university funding programs require that IP developed under the grant belongs to the university (or is jointly owned).
- **University resources:** If you used ASU computers, lab space, or equipment, ASU's IP policy may apply.
- **Student-initiated independent work:** If you developed this entirely on your own time, with your own equipment, and without university funding, you likely retain full IP ownership. But the line is blurry if you used campus Wi-Fi, library resources, etc.

**Recommendation:** Before publishing the repo or entering any commercial licensing discussions, check ASU's IP policy and consider a brief consultation with Skysong Innovations (ASU's tech transfer office). They can confirm whether ASU has any claims. This is free for ASU students and takes one meeting.

---

*This document was prepared for informational purposes and does not constitute legal advice.*
