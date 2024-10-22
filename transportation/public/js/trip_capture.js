frappe.provide('transportation');

import React, { useState } from 'react';
import { Camera } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

const TripCaptureComponent = () => {
  const [tripSheetImage, setTripSheetImage] = useState(null);
  const [deliveryNoteImage, setDeliveryNoteImage] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const captureImage = async (type) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          facingMode: 'environment',  // Prefer rear camera
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        } 
      });
      
      const video = document.createElement('video');
      video.srcObject = stream;
      await video.play();

      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      const context = canvas.getContext('2d');
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8));
      
      stream.getTracks().forEach(track => track.stop());
      
      if (type === 'tripSheet') {
        setTripSheetImage(blob);
        frappe.show_alert({
          message: '✅ Trip Sheet photo captured successfully!',
          indicator: 'green'
        });
      } else {
        setDeliveryNoteImage(blob);
        frappe.show_alert({
          message: '✅ Delivery Note photo captured successfully!',
          indicator: 'green'
        });
      }
    } catch (error) {
      console.error('Camera error:', error);
      frappe.show_alert({
        message: '❌ Camera access failed. Please check permissions and try again.',
        indicator: 'red'
      });
    }
  };

  const handleSubmit = async () => {
    if (!tripSheetImage || !deliveryNoteImage) return;
    
    setIsSubmitting(true);
    
    try {
      const formData = new FormData();
      formData.append('trip_sheet', tripSheetImage, 'trip_sheet.jpg');
      formData.append('delivery_note', deliveryNoteImage, 'delivery_note.jpg');
      
      await frappe.call({
        method: 'transportation.api.create_trip_record',
        args: {
          images: formData
        },
        callback: function(r) {
          if (r.message) {
            frappe.show_alert({
              message: '✅ Trip records submitted successfully!',
              indicator: 'green'
            });
            
            // Reset the form
            setTripSheetImage(null);
            setDeliveryNoteImage(null);
          }
        }
      });
    } catch (error) {
      console.error('Submission error:', error);
      frappe.show_alert({
        message: '❌ Failed to submit trip records. Please try again.',
        indicator: 'red'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 p-4">
      <Card className="w-full max-w-md">
        <CardContent className="p-6 space-y-6">
          {/* Trip Sheet Button */}
          <div className="flex flex-col items-center">
            <Button
              size="lg"
              className={`w-full h-24 text-lg font-bold ${tripSheetImage ? 'bg-green-600 hover:bg-green-700' : 'bg-blue-600 hover:bg-blue-700'}`}
              onClick={() => captureImage('tripSheet')}
              disabled={isSubmitting}
            >
              <Camera className="mr-2 h-8 w-8" />
              {tripSheetImage ? '✓ Trip Sheet Captured' : '1. Take Trip Sheet Picture'}
            </Button>
            {tripSheetImage && (
              <span className="text-green-600 mt-2 font-semibold">Picture 1 taken successfully!</span>
            )}
          </div>

          {/* Delivery Note Button */}
          <div className="flex flex-col items-center">
            <Button
              size="lg"
              className={`w-full h-24 text-lg font-bold ${deliveryNoteImage ? 'bg-green-600 hover:bg-green-700' : 'bg-blue-600 hover:bg-blue-700'}`}
              onClick={() => captureImage('deliveryNote')}
              disabled={isSubmitting}
            >
              <Camera className="mr-2 h-8 w-8" />
              {deliveryNoteImage ? '✓ Delivery Note Captured' : '2. Take Delivery Note Picture'}
            </Button>
            {deliveryNoteImage && (
              <span className="text-green-600 mt-2 font-semibold">Picture 2 taken successfully!</span>
            )}
          </div>

          {/* Submit Button */}
          <Button
            size="lg"
            className="w-full h-16 text-xl font-bold bg-green-600 hover:bg-green-700 disabled:bg-gray-400"
            disabled={!tripSheetImage || !deliveryNoteImage || isSubmitting}
            onClick={handleSubmit}
          >
            {isSubmitting ? 'Submitting...' : 'Submit Trip'}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};

transportation.TripCapturePage = class TripCapturePage {
    constructor(wrapper) {
        this.wrapper = wrapper;
        this.init();
    }

    init() {
        this.make();
    }

    make() {
        const component = frappe.react.Component({
            component: TripCaptureComponent
        });
        
        ReactDOM.render(
            component,
            this.wrapper
        );
    }
}