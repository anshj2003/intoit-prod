document.addEventListener("DOMContentLoaded", function () {
  const fileInput = document.getElementById("fileInput");
  const deviceNameInput = document.getElementById("deviceName");
  const fileList = document.getElementById("fileList");
  const audioPlayer = document.getElementById("audioPlayer");

  async function fetchFiles() {
    const res = await fetch("/files");
    const data = await res.json();
    return data.devices;
  }

  function createFileList(devices) {
    const fileListDiv = document.getElementById("fileList");
    fileListDiv.innerHTML = "";
    for (const [device, files] of Object.entries(devices)) {
      // Create a collapsible section for each device
      const deviceSection = document.createElement("div");
      deviceSection.classList.add("mb-4");

      const header = document.createElement("div");
      header.classList.add(
        "bg-blue-500",
        "text-white",
        "p-2",
        "cursor-pointer"
      );
      header.textContent = device;
      deviceSection.appendChild(header);

      const list = document.createElement("ul");
      list.classList.add("bg-gray-50", "p-2");
      // Initially hide the list; clicking header toggles it
      list.style.display = "none";

      header.addEventListener("click", () => {
        list.style.display = list.style.display === "none" ? "block" : "none";
      });

      // Add files (show human-friendly timestamp)
      files.forEach((file) => {
        const li = document.createElement("li");
        li.classList.add("p-1", "cursor-pointer", "hover:bg-gray-200");
        li.textContent = file.human_timestamp;
        li.addEventListener("click", () => {
          // When a file is clicked, set it as the source for the audio player.
          document.getElementById("audioPlayer").src = "/file/" + file.filename;
          document.getElementById("audioPlayer").play();
        });
        list.appendChild(li);
      });

      deviceSection.appendChild(list);
      fileListDiv.appendChild(deviceSection);
    }
  }

  // Load files on page load
  fetchFiles().then(createFileList);
});
