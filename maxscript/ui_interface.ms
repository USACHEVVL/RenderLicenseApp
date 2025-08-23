macroScript RenderNotifySetup
category:"RenderLicenseApp"
tooltip:"Render Notifier"
buttontext:"Notifier"
(
    rollout RenderNotifyRollout "Render License Notifier" width:300
    (
        edittext licenseInput "License Key:" width:280
        label statusLabel "Checking license..." width:280
        checkbox notifyStart "Notify on render start"

        button saveBtn "Save settings" width:280

        fn checkLicense key =
        (
            local url = "http://127.0.0.1:8000/check_license?license_key=" + key
            local outputFile = getDir #temp + "\\license_check_result.json"

            local cmd = "curl -s -o \"" + outputFile + "\" \"" + url + "\""
            shellLaunch "cmd.exe" ("/C " + cmd)

            sleep 0.5

            if doesFileExist outputFile then
            (
                local f = openFile outputFile
                local raw = readLine f
                close f
                deleteFile outputFile

                try (
                    local json = parseJSON raw
                    if json != undefined then
                    (
                        if (findString json.status "valid") != undefined then
                            statusLabel.text = "? License valid"
                        else
                            statusLabel.text = "? License invalid"
                    )
                ) catch (
                    statusLabel.text = "? Invalid server response"
                )
            )
            else
            (
                statusLabel.text = "? Server not available"
            )
        )

        on licenseInput entered val do
        (
            statusLabel.text = "Checking..."
            checkLicense val
        )

        fn saveSettings =
        (
            local iniPath = getDir #userScripts + "\\render_license_config.ini"
            setINISetting iniPath "RenderLicense" "license_key" licenseInput.text
            setINISetting iniPath "RenderLicense" "notify_start" (if notifyStart.checked then "true" else "false")
            messageBox ("? Settings saved!\n\nINI file:\n" + iniPath) title:"RenderLicenseApp"
        )

        fn loadSettings =
        (
            local iniPath = getDir #userScripts + "\\render_license_config.ini"
            licenseInput.text = getINISetting iniPath "RenderLicense" "license_key"
            notifyStart.checked = (getINISetting iniPath "RenderLicense" "notify_start") == "true"
            if licenseInput.text != "" then (
                statusLabel.text = "Checking..."
                checkLicense licenseInput.text
            )
        )

        on saveBtn pressed do saveSettings()

        on RenderNotifyRollout open do
        (
            loadSettings()

            callbacks.removeScripts id:#renderLicenseStart
            callbacks.removeScripts id:#renderLicenseEnd

            callbacks.addScript #preRender "renderLicense_onRenderStart()" id:#renderLicenseStart
            callbacks.addScript #postRender "renderLicense_onRenderEnd()" id:#renderLicenseEnd
        )
    )

    fn getRenderViewName =
    (
        local cam = undefined
        try (cam = renderCamera) catch (cam = undefined)
        if cam == undefined do try (cam = viewport.getCamera()) catch (cam = undefined)

        if cam != undefined then
            try (cam.name) catch ("Camera")
        else
        (
            local vt = viewport.getType()
            case vt of
            (
                #view_persp_user:  "Perspective"
                #view_ortho_user:  "Orthographic"
                #view_iso_user:    "Orthographic"
                #view_top:         "Top"
                #view_bottom:      "Bottom"
                #view_front:       "Front"
                #view_back:        "Back"
                #view_left:        "Left"
                #view_right:       "Right"
                default:           (vt as string)
            )
        )
    )

    fn renderLicense_onRenderStart =
    (
        local iniPath = getDir #userScripts + "\\render_license_config.ini"
        local notifyStart = getINISetting iniPath "RenderLicense" "notify_start"
        local license = getINISetting iniPath "RenderLicense" "license_key"

        if notifyStart == "true" then
        (
            if license != "" then
            (
                local sceneName = if maxFileName != "" then maxFileName else "Untitled"
                local cameraName = getRenderViewName()
                local startTime = localTime as string

                local logText = "?? Scene: " + sceneName + "\n" +
                                "?? View: " + cameraName + "\n" +
                                "?? Render start: " + startTime + "\n"

                messageBox logText title:"RenderLicenseApp"
            )
            else
            (
                messageBox "? License invalid. Render is unavailable." title:"RenderLicenseApp"
            )
        )
    )

    fn renderLicense_onRenderEnd =
    (
        local sceneName = if maxFileName != "" then maxFileName else "Untitled"
        local cameraName = getRenderViewName()
        local endTime = localTime as string

        local logText = "?? Scene: " + sceneName + "\n" +
                        "?? View: " + cameraName + "\n" +
                        "? Render finished: " + endTime + "\n"

        messageBox logText title:"RenderLicenseApp"
    )

    -- ?? Open the UI on macro execution
    createDialog RenderNotifyRollout
)
