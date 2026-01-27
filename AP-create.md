Creating a "Virtual AP" (Hotspot) on your Arch Linux laptop is the best solution for latency. Since your ESP32 code is hardcoded to look for `shanto`, we will create a hotspot with that exact name and password.

Here are the two best ways to do this on Arch Linux.

### Method 1: Using NetworkManager (Recommended)

Most Arch laptops use NetworkManager. You can do this entirely from the terminal.

**1. Find your Wi-Fi Interface Name**
Run this command to find your wireless card's name (it will be something like `wlan0`, `wlp3s0`, etc.):

```bash
ip link
```

**2. Create the Hotspot**
Replace `wlan0` in the first command with your actual interface name found above.

```bash
# 1. Create the connection
nmcli con add type wifi ifname wlan0 con-name shanto autoconnect yes ssid shanto

# 2. Set mode to Access Point (AP) and force 2.4GHz (Critical for ESP32)
nmcli con modify shanto 802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared

# 3. Set the password
nmcli con modify shanto wifi-sec.key-mgmt wpa-psk wifi-sec.psk shanto.py

# 4. Turn it on
nmcli con up shanto
```

**Why `band bg`?** This forces the hotspot to use **2.4 GHz**. The ESP32 **cannot** connect to 5 GHz networks, so this step is crucial.

-----

### Method 2: Using `linux-wifi-hotspot` (GUI Tool)

If you prefer a graphical interface or if NetworkManager gives you trouble, there is a popular Arch User Repository (AUR) package specifically for this.

**1. Install the tool**

```bash
yay -S linux-wifi-hotspot
```

*(Or use `paru`, `pikaur`, etc.)*

**2. Open the GUI**
Run `wihotspot` from your terminal or application menu.

**3. Configure:**

  * **SSID:** `shanto`
  * **Password:** `shanto.py`
  * **Interface:** Select your Wi-Fi card.
  * **Frequency Band:** **2.4 GHz** (Important\!)
  * Click **"Create Hotspot"**.

-----

### Verifying the Connection

Once the hotspot is running:

1.  **Power on your ESP32s.**
2.  On your laptop, check connected devices:
    ```bash
    ip neigh
    ```
    You should see the IP addresses of your ESP32 camera and controller appear here (e.g., `10.42.0.x` or `192.168.x.x`).
3.  **Update your Python Scripts:** Update the `IP_ADDRESS` in your `main.py` to match the new IPs shown in the terminal.