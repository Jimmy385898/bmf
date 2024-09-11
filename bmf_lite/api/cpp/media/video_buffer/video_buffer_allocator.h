/*
 * Copyright 2024 Babit Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef _BMFLITE_MEDIA_VIDEO_BUFFER_ALLOCATOR_H_
#define _BMFLITE_MEDIA_VIDEO_BUFFER_ALLOCATOR_H_

#include "hardware_device_context.h"
#include "video_buffer.h"

namespace bmf_lite {

class VideoBufferAllocator {
  public:
    // detroy the managed context.
    virtual ~VideoBufferAllocator() {};

    // return the device type
    virtual int
    allocVideoBuffer(int width, int height, HardwareDataInfo *data_info,
                     std::shared_ptr<HWDeviceContext> device_context,
                     VideoBuffer *&video_buffer) = 0;
    // virtual int releaseVideoBuffer(VideoBuffer* video_buffer) = 0;
};

class BMF_LITE_EXPORT AllocatorManager {
  public:
    static std::shared_ptr<VideoBufferAllocator>
    getAllocator(const MemoryType memory_type,
                 std::shared_ptr<HWDeviceContext> device_context);
};

} // namespace bmf_lite

#endif // _BMFLITE_MEDIA_VIDEO_BUFFER_ALLOCATOR_H_