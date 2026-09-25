# Optimization for Applicant Tracking Systems (ATS)

## 1. What Are ATS (Applicant Tracking Systems)?
ATS platforms (such as Gupy, Workday, Greenhouse, Taleo, and Lever) are enterprise software systems used by companies and staffing firms to receive, parse, categorize, and rank thousands of resumes before any human screening takes place.

Over 75% of resumes at large corporations and startups are rejected at the ATS screening stage due to format incompatibility or low semantic match scores with the job description.

---

## 2. ATS Parser Compatibility Principles

### What ATS Robots Can Read Perfectly
- **Linear Structure:** Continuous text, standardized section headers, and simple bullet-point lists.
- **Conventional Section Names:** Use established labels such as *Professional Objective*, *Education*, *Experience*, *Projects*, *Technical Skills*, *Languages*. "Creative" headings (e.g., "My Journey", "What I've Done") confuse parsers and cause the candidate to lose score.
- **Selectable Vector Text:** PDFs generated via LaTeX or word processors where the text can be selected and copied directly. (Never submit an image-based resume or a rasterized export.)

### What Breaks or Reduces ATS Score
- **Complex Tables and Floating Multi-Column Layouts:** Many parsers read tables horizontally end-to-end, mixing text from the left column with text from the right column.
- **Skill Progress Bars and Graphical Indicators:** Visual elements such as "Python: 80%" or "3 stars in SQL" are invisible to ATS robots and signal amateurism to technical recruiters.
- **Text Boxes and Rigid Headers/Footers:** Critical information placed in the physical page header or footer may be ignored entirely by the parser.

---

## 3. Semantic Strategy and Keyword Matching

The ATS algorithm compares the resume text against the posted job description. To maximize relevance:

1. **Exact Match and Variations:**
   - If the job requires "Python, SQL, and Docker," those exact terms must appear in the resume — both in the skills section and in the context of projects or experiences.
   - Use the full form and the acronym when relevant (e.g., *Natural Language Processing (NLP)*, *Artificial Intelligence (AI)*).

2. **Balanced Density (Contextual Keyword Density):**
   - Simply listing keywords in an isolated section at the end is not enough.
   - Modern algorithms (especially NLP-based) assign higher weight to keywords that appear associated with actions and results in bullet points (e.g., *"Developed Machine Learning models using scikit-learn"* scores higher than just *"scikit-learn"* in a loose list).

3. **Anti-Pattern: Keyword Stuffing or Hidden Text:**
   - Old techniques such as pasting job requirements in white text or an invisible font size are instantly detected by modern parsers and result in automatic disqualification for fraud.

---

## 4. ATS Checklist for Generated Resumes
- [ ] The file is a PDF generated directly from readable code/text.
- [ ] The filename is professional: `Resume_FirstName_LastName.pdf`.
- [ ] Section headings follow industry-standard vocabulary.
- [ ] All essential job requirements are reflected in the text based on the candidate's real facts.
- [ ] No hidden tables, excessive icons, or conflicting floating columns.
