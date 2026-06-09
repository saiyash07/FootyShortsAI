document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const btnScanDrive = document.getElementById("btnScanDrive");
    const btnGenerateMetadata = document.getElementById("btnGenerateMetadata");
    const btnUploadVideos = document.getElementById("btnUploadVideos");
    
    const statTotal = document.getElementById("statTotal");
    const statPending = document.getElementById("statPending");
    const statMetadata = document.getElementById("statMetadata");
    const statUploading = document.getElementById("statUploading");
    const statUploaded = document.getElementById("statUploaded");
    const statFailed = document.getElementById("statFailed");
    
    const searchBar = document.getElementById("searchBar");
    const statusFilter = document.getElementById("statusFilter");
    const videoTableBody = document.getElementById("videoTableBody");
    
    const videoModal = document.getElementById("videoModal");
    const modalFilename = document.getElementById("modalFilename");
    const modalDriveId = document.getElementById("modalDriveId");
    const modalStatusBadge = document.getElementById("modalStatusBadge");
    const modalTitleText = document.getElementById("modalTitleText");
    const modalDescriptionText = document.getElementById("modalDescriptionText");
    const modalHashtagsText = document.getElementById("modalHashtagsText");
    const modalYoutubeId = document.getElementById("modalYoutubeId");
    const modalBtnUpload = document.getElementById("modalBtnUpload");
    
    const toast = document.getElementById("toast");

    let currentVideos = [];
    let selectedVideoId = null;

    // Toast Helper
    function showToast(message, isError = false) {
        toast.textContent = message;
        if (isError) {
            toast.classList.add("error");
        } else {
            toast.classList.remove("error");
        }
        toast.classList.remove("hidden");
        setTimeout(() => {
            toast.classList.add("hidden");
        }, 4000);
    }

    // Fetch Analytics / Stats
    async function fetchStats() {
        try {
            const res = await fetch("/api/stats");
            if (!res.ok) throw new Error("Failed to fetch statistics");
            const data = await res.json();
            
            statTotal.textContent = data.total;
            statPending.textContent = data.pending;
            statMetadata.textContent = data.metadata_generated;
            statUploading.textContent = data.uploading;
            statUploaded.textContent = data.uploaded;
            statFailed.textContent = data.failed;
        } catch (err) {
            console.error("Error fetching stats:", err);
        }
    }

    // Fetch Videos List
    async function fetchVideos() {
        try {
            const q = searchBar.value;
            const status = statusFilter.value;
            let url = `/api/videos?limit=100`;
            if (q) url += `&q=${encodeURIComponent(q)}`;
            if (status) url += `&status=${encodeURIComponent(status)}`;

            const res = await fetch(url);
            if (!res.ok) throw new Error("Failed to fetch videos");
            const data = await res.json();
            
            currentVideos = data;
            renderVideosTable(data);
        } catch (err) {
            console.error("Error fetching videos:", err);
            videoTableBody.innerHTML = `<tr><td colspan="7" class="loading-state">Error loading videos.</td></tr>`;
        }
    }

    // Render Videos in Table
    function renderVideosTable(videos) {
        if (videos.length === 0) {
            videoTableBody.innerHTML = `<tr><td colspan="7" class="loading-state">No videos found.</td></tr>`;
            return;
        }

        videoTableBody.innerHTML = videos.map(video => {
            const createdDate = new Date(video.created_at).toLocaleString();
            const uploadedDate = video.uploaded_at ? new Date(video.uploaded_at).toLocaleString() : "-";
            const badgeClass = `badge-${video.status}`;
            
            return `
                <tr style="cursor: pointer;" onclick="window.viewVideoDetails(${video.id})">
                    <td class="filename-value">${video.filename}</td>
                    <td>${video.title || '<span class="text-muted">No title generated</span>'}</td>
                    <td><span class="badge ${badgeClass}">${video.status.replace("_", " ")}</span></td>
                    <td style="text-align: center;">${video.upload_attempts}</td>
                    <td>${createdDate}</td>
                    <td>${uploadedDate}</td>
                    <td>
                        <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); window.viewVideoDetails(${video.id})">View</button>
                    </td>
                </tr>
            `;
        }).join("");
    }

    // View Details Modal
    window.viewVideoDetails = function(videoId) {
        const video = currentVideos.find(v => v.id === videoId);
        if (!video) return;

        selectedVideoId = video.id;
        
        modalFilename.textContent = video.filename;
        modalDriveId.textContent = video.drive_file_id;
        modalStatusBadge.textContent = video.status.replace("_", " ");
        modalStatusBadge.className = `badge badge-${video.status}`;
        
        modalTitleText.textContent = video.title || "No Title Generated";
        modalDescriptionText.textContent = video.description || "No Description Generated";
        modalHashtagsText.textContent = video.hashtags || "No Hashtags Generated";
        
        modalYoutubeId.textContent = video.youtube_video_id || "Not Uploaded";

        // Show/hide upload button in modal
        if (video.status === 'metadata_generated' || video.status === 'failed') {
            modalBtnUpload.style.display = 'inline-flex';
        } else {
            modalBtnUpload.style.display = 'none';
        }

        videoModal.showModal();
    };

    // Trigger Drive Scan
    btnScanDrive.addEventListener("click", async () => {
        try {
            const res = await fetch("/api/scan-drive", { method: "POST" });
            if (!res.ok) throw new Error("Failed to trigger scan");
            showToast("Google Drive scan started in the background!");
            setTimeout(refreshAll, 1000);
        } catch (err) {
            showToast(err.message, true);
        }
    });

    // Trigger AI Generation
    btnGenerateMetadata.addEventListener("click", async () => {
        try {
            const res = await fetch("/api/generate-metadata", { method: "POST" });
            if (!res.ok) throw new Error("Failed to trigger metadata generation");
            showToast("Gemini metadata generation started!");
            setTimeout(refreshAll, 1000);
        } catch (err) {
            showToast(err.message, true);
        }
    });

    // Trigger Uploads
    btnUploadVideos.addEventListener("click", async () => {
        try {
            const res = await fetch("/api/upload-video", { method: "POST" });
            if (!res.ok) throw new Error("Failed to trigger YouTube upload");
            showToast("YouTube video upload queue started!");
            setTimeout(refreshAll, 1000);
        } catch (err) {
            showToast(err.message, true);
        }
    });

    // Modal Single Video Upload Action
    modalBtnUpload.addEventListener("click", async () => {
        if (!selectedVideoId) return;
        try {
            const res = await fetch(`/api/upload-video?video_id=${selectedVideoId}`, { method: "POST" });
            if (!res.ok) throw new Error("Failed to start upload");
            showToast(`Upload sequence started for video ID ${selectedVideoId}!`);
            videoModal.close();
            setTimeout(refreshAll, 1000);
        } catch (err) {
            showToast(err.message, true);
        }
    });

    // Filters & Search event listeners
    searchBar.addEventListener("input", fetchVideos);
    statusFilter.addEventListener("change", fetchVideos);

    // Fallback light-dismiss for browsers without closedby support
    if (!('closedBy' in HTMLDialogElement.prototype)) {
        videoModal.addEventListener('click', (event) => {
            if (event.target !== videoModal) return;
            const rect = videoModal.getBoundingClientRect();
            const isInside = (
                rect.top <= event.clientY &&
                event.clientY <= rect.top + rect.height &&
                rect.left <= event.clientX &&
                event.clientX <= rect.left + rect.width
            );
            if (!isInside) {
                videoModal.close();
            }
        });
    }

    // Refresh function
    function refreshAll() {
        fetchStats();
        fetchVideos();
    }

    // Initial Load & Intervals
    refreshAll();
    setInterval(refreshAll, 10000); // Auto-refresh every 10 seconds
});
