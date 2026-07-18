## 归档页“重复”投诉诊断流程

When user says `https://site/archives/ has duplicate entries`, do not assume the HTML is wrong before checking:

1. Fetch the rendered `archives/index.html` from the live site, or parse `public/archives/index.html`.
2. Extract `(href/title/date)` tuples from `<li class="post-item">` blocks.
3. Count exact title/date duplicates.
4. If `dup groups == 0`, ask user to point to the duplicated titles/links rather than continuing site edits blindly.

Typical user-perceived duplicates
- same content exists both under `/posts/...` and `/series/...`
- similar titles but different dates
- visual duplication caused by sticky/footer/banner overlap, not list duplication

Only change `layouts/_default/archives.html` after you have evidence of real rendered duplicates.
