export function responseError(response) {
  const error = new Error(response.error);
  error.detail = response.detail || "";
  return error;
}

export function attachDetails(element, detail) {
  element.querySelector("[data-error-details]")?.remove();
  if (!detail) return;
  const disclosure = document.createElement("details");
  disclosure.dataset.errorDetails = "";
  const title = document.createElement("summary");
  title.textContent = "Details";
  const text = document.createElement("pre");
  text.textContent = detail;
  disclosure.append(title, text);
  element.append(disclosure);
}
