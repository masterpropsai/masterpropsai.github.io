#!/usr/bin/env python3
"""Genera contacto.html y terminos.html (27-nov-2026). Editar el texto ACA y volver a correr:
    python scripts/gen_legales.py
Mismo molde visual que el blog. Operador y mail de contacto: los mismos de gambeta.ai."""
import os

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
MAIL = 'pronosticosarg@gmail.com'
FECHA = '27 de noviembre de 2026'
AFI = 'https://refpa96317.com/L?tag=d_5777587m_11213c_mplegal&site=5777587&ad=11213'

CSS = """:root{--bg:#0a0a0f;--card:#111118;--gold:#d4a520;--gold-l:#f0c850;--text:#f0ece0;--text-s:#a8a294;--border:rgba(212,165,32,0.18)}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.7;min-height:100vh}
.nav{position:sticky;top:0;background:rgba(10,10,15,0.94);border-bottom:1px solid var(--border);padding:14px 24px;z-index:10}
.nav-inner{max-width:780px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap}
.logo{font-family:'Orbitron',sans-serif;font-weight:900;font-size:1.15rem;color:var(--gold);text-decoration:none;letter-spacing:1px}
.nav-links{display:flex;gap:18px}
.nav-links a{color:var(--text-s);text-decoration:none;font-size:.9rem;font-weight:600;padding:4px 0}
.nav-links a:hover{color:var(--gold-l)}
.container{max-width:780px;margin:0 auto;padding:36px 24px 70px}
h1{font-family:'Orbitron',sans-serif;font-size:2rem;font-weight:900;line-height:1.2;margin-bottom:14px;overflow-wrap:anywhere}
.bajada{font-size:1.05rem;color:#e8e4d8;margin-bottom:10px}
.fecha{font-size:.85rem;color:var(--text-s);margin-bottom:26px;padding-bottom:20px;border-bottom:1px solid var(--border)}
h2{font-family:'Poppins',sans-serif;font-size:1.3rem;font-weight:800;margin-top:34px;margin-bottom:12px;line-height:1.3;color:var(--gold-l)}
p{margin-bottom:14px;font-size:1rem;color:#e8e4d8}
ul,ol{margin:0 0 16px 22px}
li{margin-bottom:8px;color:#e8e4d8}
strong{color:var(--gold-l)}
.container a,.footer a{color:var(--gold-l);text-decoration:underline}
.caja{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px 22px;margin:18px 0}
.caja h2{margin-top:0}
.boton{display:inline-block;background:var(--gold);color:#000 !important;font-weight:800;padding:12px 22px;border-radius:10px;text-decoration:none !important;margin-top:6px}
.aviso{border:1px solid var(--border);border-radius:12px;padding:16px 18px;margin-top:34px;font-size:.92rem;color:var(--text-s)}
.footer{text-align:center;padding:26px 20px 40px;border-top:1px solid var(--border);font-size:.85rem;color:var(--text-s)}
@media(max-width:480px){h1{font-size:1.5rem}.container{padding:26px 16px 60px}}"""


def pagina(slug, titulo, desc, h1, cuerpo):
    url = f'https://masterprops.ai/{slug}'
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{titulo}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{titulo}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="website">
<meta property="og:image" content="https://masterprops.ai/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<meta name="theme-color" content="#d4a520">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Orbitron:wght@700;900&family=Poppins:wght@700;800&display=swap" rel="stylesheet">
<style>
{CSS}
</style>
</head>
<body>
<nav class="nav" aria-label="Principal">
  <div class="nav-inner">
    <a href="/" class="logo">💰 MASTERPROPS</a>
    <div class="nav-links"><a href="/">Billetes</a><a href="/blog/">Blog</a><a href="/contacto">Contacto</a></div>
  </div>
</nav>
<main class="container">
<h1>{h1}</h1>
{cuerpo}
<div class="aviso">🔞 Solo para mayores de 18 años. El juego en exceso puede causar ludopatía: apostá únicamente dinero que puedas permitirte perder. MasterProps no recibe apuestas ni paga premios.</div>
</main>
<div class="footer" role="contentinfo">
  <p>💰 MasterProps — Billetes Largos · <a href="/">Billetes de hoy</a> · <a href="/blog/">Blog</a> · <a href="/contacto">Contacto</a> · <a href="/terminos">Términos</a></p>
</div>
</body>
</html>
"""


CONTACTO = f"""<p class="bajada">¿Consultas, sugerencias, un error en un billete o una propuesta de colaboración? Escribinos y te respondemos por mail.</p>
<p class="fecha">Respondemos generalmente dentro de las 48 horas hábiles.</p>

<div class="caja">
<h2>📧 Por mail</h2>
<p>Escribinos a <a href="mailto:{MAIL}?subject=MasterProps">{MAIL}</a>. Si es por un billete puntual, contanos cuál (por ejemplo «Ballena x597 del 27/11») y qué viste: así lo encontramos rápido.</p>
<a class="boton" href="mailto:{MAIL}?subject=MasterProps">Escribir un mail →</a>
</div>

<h2>¿Qué nos podés escribir?</h2>
<ul>
<li><strong>Errores:</strong> un resultado mal marcado, un cupón que no abre, un partido con la hora equivocada.</li>
<li><strong>Sugerencias:</strong> ligas, mercados o funciones que te gustaría ver.</li>
<li><strong>Prensa y colaboraciones:</strong> el historial de billetes es público; si querés usar los datos, te los preparamos con atribución a MasterProps.</li>
<li><strong>Baja de avisos:</strong> si te suscribiste a los billetes por mail y no querés recibirlos más, respondé cualquiera de esos mails o escribinos y te damos de baja.</li>
</ul>

<h2>Lo que no hacemos</h2>
<p>MasterProps no es una casa de apuestas: no tenemos tu cuenta, tu saldo ni tus apuestas. Por depósitos, retiros, bonos o verificación de cuenta tenés que hablar con el soporte de la casa donde apostaste. Tampoco damos consejos personalizados de inversión ni de cuánto apostar.</p>

<h2>Quiénes somos</h2>
<p>MasterProps es un proyecto de Grupo Gambeta, el mismo equipo de <a href="https://gambeta.ai">gambeta.ai</a>. Las reglas de uso del sitio están en los <a href="/terminos">Términos y condiciones</a>.</p>"""

TERMINOS = f"""<p class="bajada">Las reglas de uso de masterprops.ai, sin letra chica: qué ofrecemos, qué no somos y cómo se financia el sitio.</p>
<p class="fecha">Última actualización: {FECHA}</p>

<h2>1. Quiénes somos y qué es MasterProps</h2>
<p>masterprops.ai (en adelante, «el Sitio») es un servicio gratuito de análisis estadístico deportivo operado por Grupo Gambeta, el mismo equipo de <a href="https://gambeta.ai">gambeta.ai</a> (en adelante, «MasterProps», «nosotros»). El Sitio publica todos los días combinadas largas («billetes») armadas automáticamente por un modelo, junto con artículos y un historial público de resultados. Podés contactarnos desde la página de <a href="/contacto">Contacto</a>.</p>

<h2>2. Aceptación y requisitos</h2>
<p>Al usar el Sitio aceptás estos Términos. Si no estás de acuerdo, no lo utilices.</p>
<p>Tenés que tener al menos <strong>18 años</strong> (o la mayoría de edad legal de tu país, si es superior). Es tu responsabilidad saber si las apuestas deportivas son legales donde vivís y usar únicamente operadores autorizados por la autoridad de tu país. No podés usar el Sitio si la legislación de tu país lo prohíbe.</p>

<h2>3. Información, no apuestas</h2>
<p><strong>MasterProps no es una casa de apuestas.</strong> No aceptamos apuestas, no administramos fondos de juego, no pagamos premios y no intermediamos en ninguna operación. Lo que publicamos es análisis estadístico e información, de carácter orientativo y con fines de entretenimiento.</p>
<p>Los billetes se generan a partir de datos públicos y de las cuotas del mercado mediante un modelo automatizado. Las cuotas que mostramos son las registradas al momento de armar el billete: <strong>no son una oferta</strong> y pueden haber cambiado cuando entres a la casa. La decisión de apostar, y cuánto, es exclusivamente tuya.</p>

<h2>4. Cómo se financia el Sitio: enlaces de afiliado</h2>
<p>El Sitio es gratuito. Se financia con acuerdos de patrocinio y afiliación: los botones «Apostar» y los enlaces a la casa de apuestas patrocinadora (hoy, <a href="{AFI}" target="_blank" rel="noopener sponsored">DBbet</a>) son <strong>enlaces de afiliado</strong>, y podemos recibir una compensación económica cuando alguien se registra u opera a través de ellos. Esa compensación no cambia los billetes ni su historial.</p>
<p>El «cupón» de cada billete es un código que arma la apuesta dentro de la casa. Lo genera la plataforma de la casa: puede vencer, no estar disponible en tu país o quedar desactualizado si un mercado cierra o la cuota se mueve.</p>
<p>No controlamos los sitios de terceros ni sus condiciones, promociones, licencias o prácticas. Antes de registrarte en cualquier casa, verificá que esté autorizada en tu jurisdicción. Los bonos y promociones pertenecen a quien los ofrece y tienen sus propias condiciones (por ejemplo, requisitos de apuesta o «rollover»).</p>

<h2>5. Sin garantías de resultado</h2>
<p>Ningún pronóstico garantiza ganancias. Una combinada larga se pierde con una sola selección que falle: <strong>la mayoría de los billetes largos no se cobran</strong>, y por eso pagan cuotas altas. Existen rachas negativas prolongadas.</p>
<p>La «ventaja», el «edge» o la «confianza» que muestra cada billete son estimaciones del modelo, no una certeza ni una promesa. Los resultados pasados del historial no garantizan ni predicen resultados futuros. Apostá únicamente dinero que puedas permitirte perder.</p>
<p>El Sitio se ofrece «tal cual» y «según disponibilidad». No garantizamos que esté libre de errores, que los datos de terceros (marcadores, cuotas, horarios) sean exactos en todo momento ni que el servicio sea ininterrumpido.</p>

<h2>6. Historial de resultados</h2>
<p>Cada billete se guarda tal como se publicó y no se modifica después. Los resultados se marcan automáticamente con marcadores de fuentes públicas; si un partido no se puede verificar con certeza, la selección queda pendiente en lugar de darse por ganada o perdida. Si ves un resultado mal marcado, <a href="/contacto">avisanos</a> y lo corregimos.</p>

<h2>7. Avisos por mail, notificaciones y datos</h2>
<ul>
<li><strong>Mail:</strong> si dejás tu correo para recibir billetes, lo usamos solo para enviarte esos avisos. Podés darte de baja en cualquier momento respondiendo un mail o desde <a href="/contacto">Contacto</a>. No vendemos ni cedemos tu correo.</li>
<li><strong>Notificaciones:</strong> si las activás, tu navegador guarda una suscripción técnica para enviártelas. Las desactivás desde la configuración del navegador.</li>
<li><strong>Medición:</strong> usamos una herramienta de analítica (Microsoft Clarity) para saber cómo se usa el Sitio, de forma agregada.</li>
<li><strong>En tu dispositivo:</strong> guardamos preferencias (como el idioma) en el almacenamiento local del navegador.</li>
</ul>

<h2>8. Usos permitidos y prohibidos</h2>
<p>Podés usar el Sitio para tu consulta personal. Está prohibido: (a) copiar o redistribuir masivamente los billetes o el historial sin autorización; (b) usar bots o técnicas automatizadas que sobrecarguen el servicio; (c) presentar el contenido como propio o venderlo; (d) usar el Sitio para actividades ilegales en tu país.</p>

<h2>9. Propiedad intelectual</h2>
<p>La marca MasterProps, el diseño, los textos y el modelo que arma los billetes son nuestros. Los nombres y escudos de equipos, ligas y casas de apuestas pertenecen a sus titulares y se usan solo a título informativo.</p>

<h2>10. Limitación de responsabilidad</h2>
<p>En la máxima medida permitida por la ley aplicable, MasterProps no será responsable de pérdidas económicas derivadas de apuestas realizadas con base en la información del Sitio, ni de daños indirectos o lucro cesante. Nada en estos Términos limita los derechos que la legislación de consumo te reconozca de forma irrenunciable.</p>

<h2>11. Juego responsable</h2>
<p>Apostar tiene que ser un entretenimiento. Si sentís que perdiste el control, que apostás para recuperar pérdidas o que te genera problemas, pedí ayuda: en la mayoría de los países hay líneas gratuitas de atención al jugador y las casas autorizadas ofrecen herramientas de autoexclusión y límites de depósito.</p>

<h2>12. Cambios y ley aplicable</h2>
<p>Podemos modificar estos Términos publicando la versión actualizada en esta página con su fecha. Podemos suspender o interrumpir el Sitio, total o parcialmente, por mantenimiento o por causas ajenas a nuestro control.</p>
<p>Estos Términos se rigen por las leyes de Argentina, Ciudad Autónoma de Buenos Aires, sin perjuicio de las normas imperativas de protección al consumidor de tu país de residencia. Cualquier reclamo podés dirigirlo primero a <a href="mailto:{MAIL}?subject=MasterProps">{MAIL}</a>; vamos a intentar resolverlo en un plazo razonable antes de cualquier instancia formal.</p>"""

open('contacto.html', 'w', encoding='utf-8').write(pagina(
    'contacto', '📬 Contacto — MasterProps',
    'Escribinos por consultas, sugerencias, errores en un billete, prensa o colaboraciones. Respondemos por mail en 48 horas hábiles.',
    'Contacto', CONTACTO))
open('terminos.html', 'w', encoding='utf-8').write(pagina(
    'terminos', '📜 Términos y condiciones — MasterProps',
    'Reglas de uso de masterprops.ai: qué ofrecemos, qué no somos, cómo se financia el sitio con enlaces de afiliado y por qué ningún billete garantiza ganancias.',
    'Términos y condiciones', TERMINOS))
print('ok contacto.html terminos.html')
