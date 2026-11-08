import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To, From, Content, HtmlContent, PlainTextContent
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Templates
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_template(template_name: str, **context) -> str:
    try:
        tpl = env.get_template(template_name)
        return tpl.render(**context)
    except Exception as e:
        print(f"[Email] Error rendering template {template_name}: {e}")
        return ""


def _read_sendgrid_config():
    app_url = os.getenv("REACT_APP_API_URL", "http://localhost:3000")
    from_email = os.getenv("SENDGRID_FROM_EMAIL", "no-reply@olympo.io")
    from_name = os.getenv("SENDGRID_FROM_NAME", "Olympo")
    logo_url = os.getenv("SENDGRID_LOGO_URL", f"{app_url.rstrip('/')}/image.png")

    return {
        "api_key": os.getenv("SENDGRID_API_KEY"),
        "from_email": from_email,
        "from_name": from_name,
        "app_url": app_url,
        "logo_url": logo_url,
    }


def get_sendgrid_status():
    config = _read_sendgrid_config()
    api_key = config["api_key"] or ""
    return {
        "configured": bool(api_key),
        "api_key_suffix": api_key[-4:] if api_key else None,
        "from_email": config["from_email"],
        "from_name": config["from_name"],
        "app_url": config["app_url"],
        "logo_url": config["logo_url"],
    }


def _send(raw_to: str, subject: str, html_body: str, text_body: str | None = None):
    config = _read_sendgrid_config()

    if not config["api_key"]:
        print("[Email] SendGrid API key not configured; skipping send")
        return False

    if not config["from_email"]:
        print("[Email] SendGrid from email not configured; skipping send")
        return False

    message = Mail(
        from_email=From(config["from_email"], config["from_name"]),
        to_emails=To(raw_to),
        subject=subject,
    )

    # Prefer HTML but include plain text fallback
    if html_body:
        message.add_content(HtmlContent(html_body))
    if text_body:
        message.add_content(PlainTextContent(text_body))

    try:
        # Print diagnostic info (do not log the full API key)
        api_key = config.get("api_key") or ""
        api_suffix = api_key[-4:] if api_key else None
        print(f"[Email] Sending to {raw_to} from {config.get('from_email')} (api_key_suffix={api_suffix})")
        client = SendGridAPIClient(api_key)
        response = client.send(message)
        status = getattr(response, "status_code", None)
        body = getattr(response, "body", None)
        headers = getattr(response, "headers", None)

        # Try to decode body if it's bytes-like
        body_str = None
        try:
            if isinstance(body, (bytes, bytearray)):
                body_str = body.decode("utf-8", errors="replace")
            else:
                body_str = str(body)
        except Exception:
            body_str = repr(body)

        print(f"[Email] Sent to {raw_to}: status {status}")
        print(f"[Email] Response headers: {headers}")
        print(f"[Email] Response body: {body_str}")

        # Return both status and body for diagnostic endpoints which may consume this
        return {
            "ok": True,
            "status_code": status,
            "body": body_str,
            "headers": headers,
        }
    except Exception as e:
        # Try to extract richer information from the exception (HTTPError, sendgrid client, etc.)
        extra = None
        try:
            import urllib.error

            if isinstance(e, urllib.error.HTTPError):
                try:
                    body = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    body = None
                extra = {"status_code": getattr(e, "code", None), "body": body}
            else:
                # sendgrid client exceptions sometimes expose 'body' or 'args'
                body = getattr(e, "body", None)
                status = getattr(e, "status_code", None) or getattr(e, "status", None)
                extra = {"status_code": status, "body": body, "args": getattr(e, "args", None)}
        except Exception:
            extra = {"repr": str(e)}

        print(f"[Email] Error sending email to {raw_to}: {e} | extra: {extra}")
        return {"ok": False, "error": str(e), "extra": extra}


def send_welcome_email(to_email: str, to_name: str | None = None):
    subject = "Bienvenido a Olympo"
    name = to_name or "Usuario"
    config = _read_sendgrid_config()
    html = render_template(
        "welcome.html",
        name=name,
        app_url=config["app_url"],
        logo_url=config["logo_url"],
    )
    text = render_template(
        "welcome.txt",
        name=name,
        app_url=config["app_url"],
        logo_url=config["logo_url"],
    )
    return _send(to_email, subject, html, text)


def send_registration_approved_email(to_email: str, to_name: str | None = None):
    subject = "Tu cuenta fue aprobada"
    name = to_name or "Usuario"
    config = _read_sendgrid_config()
    html = render_template(
        "registration_approved.html",
        name=name,
        app_url=config["app_url"],
        logo_url=config["logo_url"],
    )
    text = render_template(
        "registration_approved.txt",
        name=name,
        app_url=config["app_url"],
        logo_url=config["logo_url"],
    )
    return _send(to_email, subject, html, text)


def send_login_alert(to_email: str, to_name: str | None = None, ip: str | None = None):
    subject = "Nuevo inicio de sesión en tu cuenta"
    name = to_name or "Usuario"
    ip_info = f" desde {ip}" if ip else ""
    config = _read_sendgrid_config()
    html = render_template(
        "login_alert.html", name=name, ip_info=ip_info, logo_url=config["logo_url"]
    )
    text = render_template(
        "login_alert.txt", name=name, ip_info=ip_info, logo_url=config["logo_url"]
    )
    return _send(to_email, subject, html, text)


def send_new_message_email(to_email: str, to_name: str | None, sender_name: str, message_text: str, chat_link: str | None = None):
    subject = f"Nuevo mensaje de {sender_name}"
    name = to_name or "Usuario"
    config = _read_sendgrid_config()
    html = render_template(
        "new_message.html",
        name=name,
        sender_name=sender_name,
        message_text=message_text,
        chat_link=chat_link,
        logo_url=config["logo_url"],
    )
    text = render_template(
        "new_message.txt",
        name=name,
        sender_name=sender_name,
        message_text=message_text,
        chat_link=chat_link,
        logo_url=config["logo_url"],
    )
    return _send(to_email, subject, html, text)


def send_investment_request_email(to_email: str, to_name: str | None, project_title: str, amount: float, investor_name: str, solicitud_id: str | None = None, project_link: str | None = None):
    subject = f"Nueva solicitud de inversión en '{project_title}'"
    name = to_name or "Emprendedor"
    monto = f"COP${amount:,.0f}" if amount is not None else ""
    config = _read_sendgrid_config()
    html = render_template(
        "investment_request.html",
        name=name,
        investor_name=investor_name,
        amount=monto,
        project_title=project_title,
        project_link=project_link,
        solicitud_id=solicitud_id,
        logo_url=config["logo_url"],
    )
    text = render_template(
        "investment_request.txt",
        name=name,
        investor_name=investor_name,
        amount=monto,
        project_title=project_title,
        project_link=project_link,
        solicitud_id=solicitud_id,
        logo_url=config["logo_url"],
    )
    return _send(to_email, subject, html, text)


def send_investment_response_email(to_email: str, to_name: str | None, project_title: str, amount: float, status: str, solicitud_id: str | None = None, project_link: str | None = None):
    """Enviar correo al inversionista cuando su solicitud es aceptada o rechazada.

    `status` debe ser 'aceptada' o 'rechazada'.
    """
    status = (status or "").lower()
    if status == "aceptada":
        subject = f"Tu solicitud fue aceptada — {project_title}"
        estado_label = "ACEPTADA ✅"
        cta_text = "Ver solicitud"
        cta_color = "#10b981"
    else:
        subject = f"Tu solicitud fue rechazada — {project_title}"
        estado_label = "RECHAZADA ❌"
        cta_text = "Ver solicitudes"
        cta_color = "#ef4444"

    name = to_name or "Inversionista"
    monto = f"COP${amount:,.0f}" if amount is not None else ""
    config = _read_sendgrid_config()

    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color:#222; margin:0; padding:0;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#f6f8fb; padding:30px 0;">
                <tr>
                    <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:8px; overflow:hidden;">
                            <tr>
                                <td style="padding:18px; text-align:center; background:#0f1724; color:#fff;">
                                    <img src="{config['logo_url']}" alt="Ambrosia" style="height:34px; object-fit:contain;" />
                                </td>
                            </tr>
                            <tr>
                                <td style="padding:20px;">
                                    <h3 style="margin-top:0;">Hola {name},</h3>
                                    <p>Tu solicitud de inversión para <strong>{project_title}</strong> por <strong>{monto}</strong> ha sido <strong>{estado_label}</strong>.</p>
                                    {f'<p><a href="{project_link}" style="display:inline-block;padding:8px 12px;background:{cta_color};color:#fff;border-radius:6px;text-decoration:none;">{cta_text}</a></p>' if project_link else ''}
                                    <p style="color:#666; font-size:13px;">ID de la solicitud: {solicitud_id or '—'}</p>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding:12px 24px; background:#fafafa; color:#888; font-size:12px; text-align:center;">© Olympo</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
    </html>
    """

    text = f"Tu solicitud para {project_title} por {monto} ha sido {estado_label}. ID: {solicitud_id or '—'}"

    return _send(to_email, subject, html, text)
