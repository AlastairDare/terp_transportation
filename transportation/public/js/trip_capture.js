frappe.provide('transportation');

transportation.TripCapturePage = class TripCapturePage {
    constructor(wrapper) {
        this.wrapper = wrapper;
        this.init();
    }

    init() {
        this.make();
        this.setup_handlers();
    }

    make() {
        this.wrapper.innerHTML = `
            <div class="page-container">
                <div class="camera-container">
                    <!-- Trip Sheet Button -->
                    <div class="camera-button-container">
                        <button class="btn btn-primary btn-lg trip-sheet-btn" style="height: 100px; width: 100%; margin-bottom: 20px;">
                            <i class="fa fa-camera" style="margin-right: 10px;"></i>
                            Take Trip Sheet Picture
                        </button>
                        <div class="trip-sheet-status"></div>
                    </div>

                    <!-- Delivery Note Button -->
                    <div class="camera-button-container">
                        <button class="btn btn-primary btn-lg delivery-note-btn" style="height: 100px; width: 100%; margin-bottom: 20px;">
                            <i class="fa fa-camera" style="margin-right: 10px;"></i>
                            Take Delivery Note Picture
                        </button>
                        <div class="delivery-note-status"></div>
                    </div>

                    <!-- Submit Button -->
                    <button class="btn btn-success btn-lg submit-btn" style="height: 80px; width: 100%;" disabled>
                        Submit Trip
                    </button>
                </div>
            </div>
        `;

        // Add some basic styles
        const style = document.createElement('style');
        style.textContent = `
            .page-container {
                padding: 20px;
                max-width: 600px;
                margin: 0 auto;
            }
            .camera-container {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }
            .camera-button-container {
                text-align: center;
            }
            .trip-sheet-status, .delivery-note-status {
                color: green;
                margin-top: 5px;
                font-weight: bold;
            }
        `;
        document.head.appendChild(style);
    }

    setup_handlers() {
        this.tripSheetImage = null;
        this.deliveryNoteImage = null;

        // Trip Sheet Button Handler
        this.wrapper.querySelector('.trip-sheet-btn').onclick = () => {
            this.capture_image('tripSheet');
        };

        // Delivery Note Button Handler
        this.wrapper.querySelector('.delivery-note-btn').onclick = () => {
            this.capture_image('deliveryNote');
        };

        // Submit Button Handler
        this.wrapper.querySelector('.submit-btn').onclick = () => {
            this.submit_images();
        };
    }

    async capture_image(type) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    facingMode: 'environment'  // Use back camera
                } 
            });

            // Create and set up video element
            const video = document.createElement('video');
            video.srcObject = stream;
            await video.play();

            // Create canvas to capture frame
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            
            // Capture frame
            const context = canvas.getContext('2d');
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            // Convert to blob
            const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8));
            
            // Stop camera
            stream.getTracks().forEach(track => track.stop());

            // Update status and store image
            if (type === 'tripSheet') {
                this.tripSheetImage = blob;
                this.wrapper.querySelector('.trip-sheet-status').textContent = '✓ Picture taken successfully!';
                this.wrapper.querySelector('.trip-sheet-btn').classList.add('btn-success');
            } else {
                this.deliveryNoteImage = blob;
                this.wrapper.querySelector('.delivery-note-status').textContent = '✓ Picture taken successfully!';
                this.wrapper.querySelector('.delivery-note-btn').classList.add('btn-success');
            }

            // Enable submit if both images are captured
            if (this.tripSheetImage && this.deliveryNoteImage) {
                this.wrapper.querySelector('.submit-btn').disabled = false;
            }

        } catch (error) {
            console.error('Camera error:', error);
            frappe.throw(__('Failed to access camera. Please check permissions and try again.'));
        }
    }

    async submit_images() {
        if (!this.tripSheetImage || !this.deliveryNoteImage) return;

        try {
            const formData = new FormData();
            formData.append('trip_sheet', this.tripSheetImage, 'trip_sheet.jpg');
            formData.append('delivery_note', this.deliveryNoteImage, 'delivery_note.jpg');

            frappe.show_alert({
                message: __('Uploading images...'),
                indicator: 'blue'
            });

            await frappe.call({
                method: 'transportation.api.create_trip_record',
                args: {
                    images: formData
                },
                callback: (r) => {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __('Trip records submitted successfully!'),
                            indicator: 'green'
                        });
                        
                        // Reset the form
                        this.tripSheetImage = null;
                        this.deliveryNoteImage = null;
                        this.wrapper.querySelector('.trip-sheet-status').textContent = '';
                        this.wrapper.querySelector('.delivery-note-status').textContent = '';
                        this.wrapper.querySelector('.submit-btn').disabled = true;
                        this.wrapper.querySelector('.trip-sheet-btn').classList.remove('btn-success');
                        this.wrapper.querySelector('.delivery-note-btn').classList.remove('btn-success');
                    } else {
                        frappe.throw(__('Failed to submit trip records'));
                    }
                }
            });

        } catch (error) {
            console.error('Submission error:', error);
            frappe.throw(__('Failed to submit trip records'));
        }
    }
};