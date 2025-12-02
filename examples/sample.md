# Sample Markdown for Translation

This is a sample Markdown file for testing the batch translation functionality.

## Text Elements to Translate

- Headers at various levels
- Paragraphs with text content
- List items like this one
- Blockquotes: > This is a blockquote that should be translated
- Tables:

| Header 1     | Header 2     |
|--------------|--------------|
| Row 1 Cell 1 | Row 1 Cell 2 |
| Row 2 Cell 1 | Row 2 Cell 2 |

## Code Preservation

Code blocks should be preserved without translation:

```javascript
function helloWorld() {
    console.log("Hello, world!");
}
```

```python
def greet(name):
    print(f"Hello, {name}!")
```

## Inline Elements

Inline `code` should be preserved, but regular text like *this* should be translated.

## Language-Specific Features

HTML within Markdown should be handled correctly:

<div class="note">
    This is an HTML div within Markdown that should be translated.
</div>