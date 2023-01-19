<?php

namespace leonverschuren\Lenex;
require_once 'vendor/autoload.php';

$reader = new Reader();
$parser = new Parser();
$result = $parser->extractMeet($reader->read('../processed_data/test.lef'));
//$result = $parser->extractMeet($reader->read('../examples/scOK.lef'));

print_r($result);