# Official Kasm 1.17.0, linux/amd64 manifest:
# sha256:366a6a02c3d8dcba4fa492acbf8ad5cd71c8b85884532f8d767b49e39ffea1fe
# The tutorial's registry.lazycat.cloud/kasm-debian-bookworm:0.0.1 requires auth.
FROM --platform=linux/amd64 kasmweb/core-debian-bookworm:1.17.0
USER root
RUN usermod -l lazycat -d /home/lazycat kasm-user \
    && mkdir -p /home/lazycat \
    && cp -a /home/kasm-default-profile/. /home/lazycat/ \
    && sed -i 's/kasm_user/lazycat/g' /dockerstartup/vnc_startup.sh \
    && mkdir -p /home/lazycat/.vnc /home/lazycat/.config/autostart /home/lazycat/Desktop \
    && chown -R 1000:1000 /home/lazycat \
    && chmod -R u+rwX /home/lazycat
ENV HOME=/home/lazycat \
    VNC_RESOLUTION=1440x900 \
    VNC_PW=lazycat \
    VNCOPTIONS="-PreferBandwidth -disableBasicAuth -DynamicQualityMin=4 -DynamicQualityMax=7 -DLP_ClipDelay=0 -sslOnly=0"
WORKDIR /home/lazycat
COPY vendor/quote-desktop/ /opt/quote-desktop/
COPY icon.png /opt/quote-desktop/icon.png
COPY start-quote.sh /usr/local/bin/start-quote
COPY --chown=1000:1000 kasmvnc.yaml /home/lazycat/.vnc/kasmvnc.yaml
COPY --chown=1000:1000 quote-desktop.desktop /home/lazycat/.config/autostart/quote-desktop.desktop
COPY --chown=1000:1000 quote-desktop.desktop /home/lazycat/Desktop/quote-desktop.desktop
RUN chmod 755 /usr/local/bin/start-quote /opt/quote-desktop/quote-desktop \
        /opt/quote-desktop/chrome_crashpad_handler /opt/quote-desktop/chrome-sandbox \
        /home/lazycat/Desktop/quote-desktop.desktop \
    && ldd /opt/quote-desktop/quote-desktop > /tmp/quote-ldd.txt \
    && ! grep -q 'not found' /tmp/quote-ldd.txt \
    && fc-match 'Noto Sans CJK SC' | grep -q 'NotoSansCJK'
# No passwordless sudo is needed: lzcos >=1.6 maps persistent ownership via run_as.
USER 1000:1000
# The core image references a nonexistent custom kasm_startup.sh. XFCE autostart
# is our only app launch mechanism; let vnc_startup supervise the desktop itself.
ENTRYPOINT ["/dockerstartup/kasm_default_profile.sh", "/dockerstartup/vnc_startup.sh"]
CMD ["--wait"]
