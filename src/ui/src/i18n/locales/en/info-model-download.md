
A Knowledge Pack takes the event detection model you generated in the pipeline and transforms it into a binary or library file that can be run on your hardware device at the edge. Once the Knowledge Pack is on your hardware device, it starts outputting classification IDs that correspond to your events of interest.

HW Platform
-----------

SensiML Knowledge Packs are not locked to any specific hardware platform. This feature allows you to choose the platform where you will deploy your Knowledge Pack. Some fields (Processor, Float Options, Compiler) get default values that depend on the selected HW platform.

Arm/GCC Compilers produces binaries with options in regards to floating-point operations:

* **None** -  ``-mfloat-abi=soft`` Full software floating-point. The compiler will not generate any FPU instructions and the ``-mfpu=`` option is ignored. Function calls are generated by passing floating-point arguments in integer registers.

* **Soft FP** -  ``-mfloat-abi=softfp`` Hardware floating-point using the soft floating-point ABI. The compiler will generate FPU instructions according to the -mfpu= option. Function calls are generated by passing floating-point arguments in integer registers. This means ``soft`` and ``softfp`` may be intermixed.

* **Hard FP** -  ``-mfloat-abi=hard`` Full hardware floating-point. The compiler will generate FPU instructions according to the ``-mfpu=`` option. Function calls are generated by passing floating-point arguments in FPU registers. This means hard and softfp cannot be intermixed; neither can hard and soft.

Format
------

We provide three formats to interface with your model when you generate a Knowledge Pack. The available format options depend on the device or compiler that you are using. See details about each of the three formats below.

**1. Binary**

Generates application firmware that is ready to flash to your device. Includes the application, Knowledge Pack, sensor configuration/drivers, and classification output for the target device.

**2. Library**

Generates a library and header files with function APIs that can be linked into your application firmware. See the links below for useful information on the Library format.

**3. Source**

Generates a Makefile and the C/C++ source code files for the Knowledge Pack APIs. See the :doc:`SensiML Embedded SDK Documentation</knowledge-packs/sensiml-embedded-sdk>` for more information on the Source format.

> **Source** is only available to specific subscription plans. See more details at `<https://sensiml.com/plans/>`_

Application
-----------

**Application** - Application is the example application for supported platforms that allows an example binary to be built for testing.

Classification Output
---------------------

**Output** - Output corresponds to how your events get broadcasted from the hardware device and how you want to connect to your device. There are three main outputs: Bluetooth-LE, Serial, and Wi-Fi (TCP/IP).

Debug Output
------------

When building a Knowledge Pack there is a debug option that will log extra information like feature vectors, debug messages, and error messages over a serial connection to help you debug the events of interest on a device. To enable this, set Debug to True in the Advanced Settings when you download your Knowledge Pack.

After flashing your device with a Knowledge Pack, debug information can be viewed by connecting to the virtual COM port in a terminal application.

[See Documentation](https://sensiml.com/documentation/analytics-studio/generating-a-knowledge-pack.html)