# Zenn マークダウンチートシート

**参照**: [公式ガイド](https://zenn.dev/zenn/articles/markdown-guide)

---

## 見出し

```markdown
## 見出し2（h1はタイトルで使用済み）
### 見出し3
#### 見出し4
```

---

## 強調・装飾

| 記法 | 結果 |
|------|------|
| `*イタリック*` | *イタリック* |
| `~~打ち消し~~` | ~~打ち消し~~ |
| `` `code` `` | `code` |

:::message alert
`**太字**` は使用禁止（AI生成パターン）
:::

---

## メッセージボックス（独自記法）

```markdown
:::message
通常のメッセージ
:::

:::message alert
警告メッセージ
:::
```

**用途**: 注意喚起、補足情報（`**強調**` の代替）

---

## アコーディオン（独自記法）

```markdown
:::details タイトル
折りたたみ内容
:::
```

ネスト時は `::::details` のようにコロンを増やす

---

## コードブロック

````markdown
```javascript:ファイル名.js
const example = "ファイル名表示";
```

```diff javascript
- const old = "削除行";
+ const new = "追加行";
```
````

---

## テーブル

```markdown
| 左寄せ | 中央 | 右寄せ |
|:-------|:----:|-------:|
| A      | B    | C      |
```

---

## 埋め込み

| 種類 | 記法 |
|------|------|
| リンクカード | URL単独行、または `@[card](URL)` |
| YouTube | 動画URL単独行 |
| X/Twitter | ポストURL単独行 |
| GitHub | ファイルURL（`#L10-L20` で行指定可） |
| Gist | `@[gist](URL)` |
| mermaid | ` ```mermaid ` |

---

## 数式（KaTeX）

```markdown
$$
e^{i\pi} + 1 = 0
$$

インライン: $E = mc^2$
```

---

## 脚注

```markdown
本文中の参照[^1]

[^1]: 脚注の内容
```

---

## 画像

```markdown
![alt](URL)
![alt](URL =250x)  <!-- 幅指定 -->
*キャプション*
```

---

## HTMLコメント

```markdown
<!-- この部分は表示されない -->
```

複数行は非対応

---

## 制限事項

- mermaidブロック: 2000字以内、Chain数10以下
- 見出し1（#）: 使用不可（タイトルがh1）
