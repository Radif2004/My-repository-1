async function uploadPDF() {
  const file = document.getElementById("pdfInput").files[0];
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("/api/upload-pdf", {
    method: "POST",
    headers: { "X-API-Key": "resource-app-copilot-key-2024" },
    body: formData
  });
  const data = await res.json();
  document.getElementById("output").innerText = data.summary;
}
