(function () {
  function clean(value, fallback) {
    return typeof value === "string" && value.trim() ? value.trim() : fallback;
  }

  function wrapText(context, text, maxWidth, maxLines) {
    const lines = [];
    let line = "";
    for (const character of text) {
      const candidate = line + character;
      if (line && context.measureText(candidate).width > maxWidth) {
        lines.push(line);
        line = character;
        if (lines.length === maxLines) break;
      } else {
        line = candidate;
      }
    }
    if (lines.length < maxLines && line) lines.push(line);
    if (lines.length === maxLines && lines.join("").length < text.length) {
      lines[maxLines - 1] = lines[maxLines - 1].slice(0, -1) + "\u2026";
    }
    return lines.length ? lines : ["\u4e66\u7c4d\u63a8\u8350"];
  }

  window.createPlaceholderCover = function (book, className) {
    const canvas = document.createElement("canvas");
    canvas.width = 420;
    canvas.height = 630;
    const context = canvas.getContext("2d");
    const title = clean(book && book.title, "\u4e66\u7c4d\u63a8\u8350");
    const author = clean(book && book.author, "Paige Book Daily");

    context.fillStyle = "#efe7da";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.fillStyle = "#fffdf8";
    context.strokeStyle = "#dccdb9";
    context.lineWidth = 2;
    context.beginPath();
    context.roundRect(28, 28, 364, 574, 18);
    context.fill();
    context.stroke();

    context.textAlign = "center";
    context.fillStyle = "#7a4f2c";
    context.font = "18px Arial, sans-serif";
    context.fillText("PAIGE BOOK DAILY", 210, 94);

    context.fillStyle = "#23201c";
    context.font = "700 34px Arial, 'Microsoft YaHei', sans-serif";
    const titleLines = wrapText(context, title, 308, 5);
    titleLines.forEach((line, index) => context.fillText(line, 210, 204 + index * 48));

    context.fillStyle = "#71695f";
    context.font = "22px Arial, 'Microsoft YaHei', sans-serif";
    const authorLines = wrapText(context, author, 280, 2);
    authorLines.forEach((line, index) => context.fillText(line, 210, 462 + index * 32));
    context.strokeStyle = "#d4b895";
    context.lineWidth = 2;
    context.beginPath();
    context.moveTo(126, 548);
    context.lineTo(294, 548);
    context.stroke();

    const image = document.createElement("img");
    image.className = className;
    image.src = canvas.toDataURL("image/png");
    image.alt = `\u300a${title}\u300b\u5c01\u9762`;
    return image;
  };
})();